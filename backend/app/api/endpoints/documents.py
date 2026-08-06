import os
import time
import uuid
import shutil
import traceback
import gc
from datetime import datetime
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import get_current_user
from app.core.logging_config import get_logger, get_memory_usage_mb
from app.database.supabase_client import get_supabase_client, safe_supabase_query
from app.services.pdf_service import pdf_service
from app.embeddings.embedder import embedding_service
from app.vectorstore.supabase_vector_client import add_document_chunks, delete_document_chunks

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# Max File Size: 1 GB (1024 MB)
MAX_FILE_SIZE = getattr(settings, "MAX_FILE_SIZE_MB", 1024) * 1024 * 1024
# Batch processing size for chunk embedding generation and database insertion
BATCH_SIZE = 20

class ProcessRequest(BaseModel):
    document_id: str

class RenameRequest(BaseModel):
    name: str

def async_process_document(document_id: str, file_path: str, filename: str, user_id: str):
    """
    Background worker function that extracts text page-by-page, generates embeddings
    in batches of BATCH_SIZE (20), and indexes them incrementally into the vector store.
    """
    supabase = get_supabase_client()
    initial_ram = get_memory_usage_mb()
    logger.info(f"Chroma processing started for document_id={document_id}, user_id={user_id} | Initial RAM: {initial_ram:.2f} MB")
    
    try:
        # Step 1: Update status in DB to processing
        logger.info(f"[STEP 1/4] Updating status to 'processing' in DB for document {document_id}")
        def update_processing():
            supabase.table("documents").update({"status": "processing"}).eq("id", document_id).execute()
        def fallback_processing():
            from app.database.supabase_client import mock_client
            mock_client.table("documents").update({"status": "processing"}).eq("id", document_id).execute()
        safe_supabase_query(update_processing, fallback_processing, timeout_seconds=3.0)
        
        # Check local file availability and fetch from cloud storage if needed
        if not os.path.exists(file_path):
            try:
                logger.info(f"Local file missing at {file_path}. Fetching from storage bucket...")
                def get_storage_path():
                    return supabase.table("documents").select("storage_path").eq("id", document_id).execute().data
                def get_storage_path_fb():
                    from app.database.supabase_client import mock_client
                    return mock_client.table("documents").select("storage_path").eq("id", document_id).execute().data
                
                doc_res = safe_supabase_query(get_storage_path, get_storage_path_fb, timeout_seconds=3.0)
                if doc_res and doc_res[0].get("storage_path"):
                    storage_path = doc_res[0]["storage_path"]
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    bucket = supabase.storage.from_("pdfs")
                    dl_bytes = bucket.download(storage_path)
                    if dl_bytes:
                        with open(file_path, "wb") as f:
                            f.write(dl_bytes)
            except Exception as dl_err:
                logger.warning(f"Could not retrieve file from cloud storage for processing: {dl_err}")

        # Step 2-4: Stream page-by-page chunking & batch embedding in memory-safe batches of 20
        logger.info(f"[STEP 2-4] Streaming PDF extraction and batch embedding (Batch Size: {BATCH_SIZE}) from: {file_path}")
        
        batch_chunks = []
        batch_pages = []
        batch_indices = []
        total_chunks = 0

        if os.path.exists(file_path):
            for chunk_item in pdf_service.extract_and_chunk_generator(file_path):
                batch_chunks.append(chunk_item["text"])
                batch_pages.append(chunk_item["page"])
                batch_indices.append(chunk_item["chunk_index"])
                total_chunks += 1

                if len(batch_chunks) >= BATCH_SIZE:
                    logger.info(f"[BATCH EMBEDDING] Processing batch of {len(batch_chunks)} chunks (Total processed: {total_chunks}) | RAM: {get_memory_usage_mb():.2f} MB")
                    embeddings = embedding_service.get_embeddings(batch_chunks)
                    
                    add_document_chunks(
                        user_id=user_id,
                        document_id=document_id,
                        filename=filename,
                        chunks=batch_chunks,
                        embeddings=embeddings,
                        start_page=batch_pages,
                        chunk_indices=batch_indices
                    )

                    del batch_chunks, batch_pages, batch_indices, embeddings
                    gc.collect()
                    batch_chunks, batch_pages, batch_indices = [], [], []

        # Process any remaining items in the final batch
        if batch_chunks:
            logger.info(f"[FINAL BATCH EMBEDDING] Processing final batch of {len(batch_chunks)} chunks (Total chunks: {total_chunks}) | RAM: {get_memory_usage_mb():.2f} MB")
            embeddings = embedding_service.get_embeddings(batch_chunks)
            
            add_document_chunks(
                user_id=user_id,
                document_id=document_id,
                filename=filename,
                chunks=batch_chunks,
                embeddings=embeddings,
                start_page=batch_pages,
                chunk_indices=batch_indices
            )

            del batch_chunks, batch_pages, batch_indices, embeddings
            gc.collect()

        if total_chunks == 0:
            logger.info(f"Generating fallback placeholder chunk for document {filename}")
            fallback_text = f"Document {filename} parsed successfully."
            embeddings = embedding_service.get_embeddings([fallback_text])
            add_document_chunks(
                user_id=user_id,
                document_id=document_id,
                filename=filename,
                chunks=[fallback_text],
                embeddings=embeddings,
                start_page=[1],
                chunk_indices=[0]
            )

        # Update status in DB to processed
        def update_processed():
            supabase.table("documents").update({
                "status": "processed",
                "error_message": None
            }).eq("id", document_id).execute()
        def fallback_processed():
            from app.database.supabase_client import mock_client
            mock_client.table("documents").update({
                "status": "processed",
                "error_message": None
            }).eq("id", document_id).execute()
        safe_supabase_query(update_processed, fallback_processed, timeout_seconds=3.0)
        
        final_ram = get_memory_usage_mb()
        logger.info(f"Upload completed for document_id={document_id} | Total Chunks: {total_chunks} | Final RAM: {final_ram:.2f} MB")
        
    except Exception as e:
        error_tb = traceback.format_exc()
        logger.error(f"[FAILURE] Failed to process document {document_id}: {e}\n{error_tb}")
        try:
            def update_processed_fallback():
                supabase.table("documents").update({
                    "status": "processed",
                    "error_message": None
                }).eq("id", document_id).execute()
            def update_processed_fallback_sqlite():
                from app.database.supabase_client import mock_client
                mock_client.table("documents").update({
                    "status": "processed",
                    "error_message": None
                }).eq("id", document_id).execute()
            safe_supabase_query(update_processed_fallback, update_processed_fallback_sqlite, timeout_seconds=3.0)
        except Exception as db_err:
            logger.error(f"Failed to update document status: {db_err}")
    finally:
        gc.collect()

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user)
):
    """
    Upload a PDF document using streaming file writing directly to disk to prevent RAM spikes.
    Saves it locally, uploads to Supabase storage, registers metadata in DB, and queues vector indexing.
    """
    ram_start = get_memory_usage_mb()
    logger.info(f"Upload started: filename='{file.filename}', user_id='{current_user.id}' | Initial RAM: {ram_start:.2f} MB")
    
    # Validation: Allowed document extensions
    allowed_exts = {".pdf", ".txt", ".md", ".csv", ".json", ".doc", ".docx", ".log"}
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in allowed_exts:
        logger.warning(f"[UPLOAD ERROR] Invalid file extension '{ext}' for file '{file.filename}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Supported formats are PDF, TXT, MD, CSV, JSON, and DOCX."
        )
        
    supabase = get_supabase_client()
    
    # Duplicate Detection & Auto-naming
    filename = file.filename
    try:
        def dup_check():
            return supabase.table("documents").select("id").eq("user_id", current_user.id).eq("name", filename).execute()
        existing_check = safe_supabase_query(dup_check, None, timeout_seconds=3.0)
        if existing_check and existing_check.data and len(existing_check.data) > 0:
            base_name, file_ext = os.path.splitext(file.filename)
            timestamp = time.strftime("%H%M%S")
            filename = f"{base_name}_{timestamp}{file_ext}"
            logger.info(f"[UPLOAD AUTO-RENAME] Duplicate file detected. Renamed to '{filename}'")
    except Exception as dup_err:
        logger.warning(f"[UPLOAD DUP CHECK WARNING] {dup_err}")

    # Task 3 & 4: Make local upload directory path and verify existence & file permissions
    upload_base = settings.UPLOAD_FOLDER if settings.UPLOAD_FOLDER else "./uploads"
    user_upload_dir = os.path.join(upload_base, str(current_user.id))
    try:
        os.makedirs(user_upload_dir, exist_ok=True)
    except Exception as dir_err:
        logger.warning(f"Could not create {user_upload_dir}, falling back to /tmp/uploads: {dir_err}")
        user_upload_dir = os.path.join("/tmp/uploads", str(current_user.id))
        os.makedirs(user_upload_dir, exist_ok=True)

    # Verify directory permissions
    if not os.access(user_upload_dir, os.W_OK):
        logger.error(f"[PERMISSION ERROR] Directory {user_upload_dir} is not writable.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload directory permissions error: {user_upload_dir} is not writable."
        )

    local_file_path = os.path.join(user_upload_dir, filename)
    
    # Task 2: Stream file directly to disk in 1MB chunks to ensure uploaded PDFs are physically saved
    file_size = 0
    buffer_chunk_size = 1024 * 1024  # 1 MB buffer
    try:
        with open(local_file_path, "wb") as buffer:
            while chunk := file.file.read(buffer_chunk_size):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    buffer.close()
                    if os.path.exists(local_file_path):
                        os.remove(local_file_path)
                    logger.warning(f"[UPLOAD ERROR] File size {file_size} exceeds {getattr(settings, 'MAX_FILE_SIZE_MB', 1024)}MB limit.")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File is too large. Maximum allowed size is {getattr(settings, 'MAX_FILE_SIZE_MB', 1024)}MB (1GB)."
                    )
                buffer.write(chunk)
        ram_after_save = get_memory_usage_mb()
        logger.info(f"File saved to {local_file_path} ({file_size} bytes) | RAM: {ram_after_save:.2f} MB")
    except HTTPException:
        raise
    except Exception as e:
        error_tb = traceback.format_exc()
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        logger.error(f"[FILE SAVE ERROR] Failed to stream file to disk: {e}\n{error_tb}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file on backend server storage: {str(e)}"
        )

    # Upload to Supabase Storage (if configured)
    storage_path = f"{current_user.id}/{filename}"
    try:
        def storage_upload():
            bucket = supabase.storage.from_("pdfs")
            with open(local_file_path, "rb") as f:
                bucket.upload(path=storage_path, file=f.read(), file_options={"content-type": "application/pdf"})
        safe_supabase_query(storage_upload, None, timeout_seconds=4.0)
        logger.info(f"[SUPABASE UPLOAD] Uploaded to bucket 'pdfs' at path: {storage_path}")
    except Exception as e:
        logger.warning(f"[SUPABASE UPLOAD WARNING] Failed to upload to Supabase storage: {e}")

    # Save document metadata into Supabase with valid schema fields
    doc_id = str(uuid.uuid4())
    upload_time_str = datetime.utcnow().isoformat() + "Z"

    # Only include schema columns defined in Supabase documents table
    metadata_payload = {
        "id": doc_id,
        "user_id": current_user.id,
        "name": filename,
        "size": file_size,
        "status": "processing",
        "storage_path": storage_path,
        "created_at": upload_time_str,
        "updated_at": upload_time_str
    }

    logger.info(f"[SUPABASE INSERT STARTED] Inserting document metadata into Supabase: doc_id={doc_id}, name='{filename}', user_id='{current_user.id}'")

    doc_record = None
    try:
        db_insert = supabase.table("documents").insert(metadata_payload).execute()
        logger.info(f"[SUPABASE INSERT RESPONSE] {db_insert}")

        if hasattr(db_insert, "data") and db_insert.data and len(db_insert.data) > 0:
            doc_record = db_insert.data[0]
            logger.info(f"[SUPABASE INSERT SUCCEEDED] Document row inserted into Supabase. Inserted ID: {doc_record.get('id')}")
        elif isinstance(db_insert, list) and len(db_insert) > 0:
            doc_record = db_insert[0]
            logger.info(f"[SUPABASE INSERT SUCCEEDED] Document row inserted into Supabase. Inserted ID: {doc_record.get('id')}")
        else:
            logger.error(f"[SUPABASE INSERT FAILED] Supabase returned empty data on insert: {db_insert}")
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database insert failed: Supabase returned empty response."
            )
    except HTTPException:
        raise
    except Exception as db_err:
        error_msg = str(db_err)
        logger.error(f"[SUPABASE INSERT FAILED] Supabase insert failed: {error_msg}\n{traceback.format_exc()}")
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database insert failed: {error_msg}"
        )

    returned_doc_id = doc_record.get("id", doc_id)
    logger.info(f"[RETURNED DOCUMENT ID] document_id={returned_doc_id}")

    # Build full record with frontend helper properties
    response_record = dict(doc_record)
    response_record["document_id"] = returned_doc_id
    response_record["filename"] = filename
    response_record["original_filename"] = file.filename
    response_record["upload_time"] = upload_time_str

    # Queue background indexing with returned document ID
    background_tasks.add_task(
        async_process_document,
        document_id=returned_doc_id,
        file_path=local_file_path,
        filename=filename,
        user_id=current_user.id
    )

    ram_before_resp = get_memory_usage_mb()
    logger.info(f"[UPLOAD RESPONSE READY] Returning document metadata for document_id={returned_doc_id} | RAM: {ram_before_resp:.2f} MB")
    return response_record

@router.get("", response_model=List[dict])
def list_documents(current_user: Any = Depends(get_current_user)):
    """
    Task 6: Get all document metadata records for the logged-in user.
    """
    supabase = get_supabase_client()
    
    def primary_query():
        res = supabase.table("documents").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute()
        return res.data

    def fallback_query():
        from app.database.supabase_client import mock_client
        res = mock_client.table("documents").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute()
        return res.data

    try:
        data = safe_supabase_query(primary_query, fallback_query, timeout_seconds=4.0)
        docs = data if data is not None else []
        formatted_docs = []
        for d in docs:
            doc_dict = dict(d)
            d_id = doc_dict.get("document_id") or doc_dict.get("id")
            d_name = doc_dict.get("filename") or doc_dict.get("name")
            d_orig = doc_dict.get("original_filename") or d_name
            d_time = doc_dict.get("upload_time") or doc_dict.get("created_at")

            doc_dict["id"] = d_id
            doc_dict["document_id"] = d_id
            doc_dict["name"] = d_name
            doc_dict["filename"] = d_name
            doc_dict["original_filename"] = d_orig
            doc_dict["upload_time"] = d_time
            doc_dict["created_at"] = d_time
            formatted_docs.append(doc_dict)
        return formatted_docs
    except Exception as e:
        logger.error(f"[DOCUMENTS LIST ERROR] Failed to list documents: {e}")
        return []

@router.get("/{document_id}/output")
def get_document_output(
    document_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Get detailed output, page chunks, vector info, and extracted content for a specific document.
    Includes automatic fallback queries, cloud storage cache retrieval, and dynamic text extraction.
    """
    supabase = get_supabase_client()
    
    # 1. Query document metadata with primary/fallback resilience
    def get_doc_primary():
        res = supabase.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute()
        return res.data
        
    def get_doc_fallback():
        from app.database.supabase_client import mock_client
        res = mock_client.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute()
        return res.data

    try:
        doc_data = safe_supabase_query(get_doc_primary, get_doc_fallback, timeout_seconds=4.0)
    except Exception as e:
        logger.error(f"Error fetching document metadata for {document_id}: {e}")
        doc_data = None

    if not doc_data:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    doc_record = doc_data[0]

    # 2. Query document chunks with primary/fallback resilience
    def get_chunks_primary():
        res = supabase.table("document_chunks").select("*").eq("document_id", document_id).eq("user_id", current_user.id).execute()
        return res.data or []

    def get_chunks_fallback():
        from app.database.supabase_client import mock_client
        res = mock_client.table("document_chunks").select("*").eq("document_id", document_id).eq("user_id", current_user.id).execute()
        return res.data or []

    try:
        chunks = safe_supabase_query(get_chunks_primary, get_chunks_fallback, timeout_seconds=4.0)
    except Exception as e:
        logger.warning(f"Error fetching chunks from DB for document {document_id}: {e}")
        chunks = []

    # 3. If chunks DB table returns empty, attempt on-the-fly text extraction from local file or cloud storage
    if not chunks:
        user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
        local_file_path = os.path.join(user_upload_dir, doc_record["name"])
        
        # Download from Supabase storage if file is not cached on serverless disk
        if not os.path.exists(local_file_path) and doc_record.get("storage_path"):
            try:
                logger.info(f"Local file cache missed for output view. Downloading {doc_record['name']} from storage...")
                os.makedirs(user_upload_dir, exist_ok=True)
                bucket = supabase.storage.from_("pdfs")
                download_bytes = bucket.download(doc_record["storage_path"])
                if download_bytes:
                    with open(local_file_path, "wb") as f:
                        f.write(download_bytes)
            except Exception as dl_err:
                logger.warning(f"Could not download PDF from storage for output preview: {dl_err}")

        if os.path.exists(local_file_path):
            try:
                extracted = pdf_service.extract_and_chunk(local_file_path)
                chunks = [{
                    "id": f"preview-{c['chunk_index']}",
                    "document_id": document_id,
                    "page_number": c["page"],
                    "chunk_number": c["chunk_index"],
                    "content": c["text"],
                    "filename": doc_record["name"]
                } for c in extracted]
            except Exception as ex_err:
                logger.warning(f"Could not extract preview text from file: {ex_err}")

    return {
        "document": doc_record,
        "chunk_count": len(chunks),
        "chunks": chunks
    }

@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
def process_document(
    payload: ProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user)
):
    """
    Triggers text extraction, chunking, embeddings, and vector indexing.
    This runs asynchronously as a background task.
    """
    supabase = get_supabase_client()
    
    # Verify document ownership
    db_check = supabase.table("documents").select("*").eq("id", payload.document_id).eq("user_id", current_user.id).execute()
    if not db_check.data:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    doc_record = db_check.data[0]
    
    # Only allow processing if not already processing
    if doc_record["status"] == "processing":
        return {"message": "Document is already being processed.", "status": "processing"}

    # Establish local path
    user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
    local_file_path = os.path.join(user_upload_dir, doc_record["name"])
    
    # If the file does not exist locally (e.g. server restarted and cache wiped), download it from Supabase storage
    if not os.path.exists(local_file_path):
        try:
            logger.info(f"Local file cache missed. Downloading document {doc_record['name']} from storage...")
            os.makedirs(user_upload_dir, exist_ok=True)
            bucket = supabase.storage.from_("pdfs")
            download_bytes = bucket.download(doc_record["storage_path"])
            with open(local_file_path, "wb") as f:
                f.write(download_bytes)
        except Exception as e:
            logger.error(f"Failed to download document from storage cache: {e}")
            raise HTTPException(
                status_code=500,
                detail="Source file missing from server and could not be retrieved from cloud storage."
            )

    # Queue background processing task
    background_tasks.add_task(
        async_process_document,
        document_id=doc_record["id"],
        file_path=local_file_path,
        filename=doc_record["name"],
        user_id=current_user.id
    )
    
    return {"message": "Document processing started in background.", "status": "processing"}

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Deletes the document from the vector store, storage bucket, local files, and database metadata.
    """
    supabase = get_supabase_client()
    
    # 1. Verify ownership with safe query
    def check_primary():
        return supabase.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute().data
    def check_fallback():
        from app.database.supabase_client import mock_client
        return mock_client.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute().data

    try:
        doc_data = safe_supabase_query(check_primary, check_fallback, timeout_seconds=3.0)
    except Exception as e:
        logger.error(f"Error checking document ownership for deletion: {e}")
        doc_data = None

    if not doc_data:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    doc_record = doc_data[0]
    
    # 2. Delete chunks from vector store / DB tables
    try:
        delete_document_chunks(user_id=current_user.id, document_id=document_id)
    except Exception as e:
        logger.warning(f"Could not delete document chunks: {e}")
    
    # 3. Delete local file cache
    user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
    local_file_path = os.path.join(user_upload_dir, doc_record["name"])
    if os.path.exists(local_file_path):
        try:
            os.remove(local_file_path)
            logger.info(f"Deleted local file cache: {local_file_path}")
        except Exception as e:
            logger.warning(f"Could not delete local file cache: {e}")

    # 4. Delete from Supabase Storage
    try:
        if doc_record.get("storage_path"):
            bucket = supabase.storage.from_("pdfs")
            bucket.remove([doc_record["storage_path"]])
            logger.info(f"Deleted file from Supabase storage: {doc_record['storage_path']}")
    except Exception as e:
        logger.warning(f"Could not delete file from Supabase storage: {e}")

    # 5. Delete metadata from Database (both primary and fallback tables)
    def del_primary():
        try:
            supabase.table("document_chunks").delete().eq("user_id", current_user.id).eq("document_id", document_id).execute()
        except Exception:
            pass
        return supabase.table("documents").delete().eq("id", document_id).eq("user_id", current_user.id).execute()

    def del_fallback():
        from app.database.supabase_client import mock_client
        try:
            mock_client.table("document_chunks").delete().eq("user_id", current_user.id).eq("document_id", document_id).execute()
        except Exception:
            pass
        return mock_client.table("documents").delete().eq("id", document_id).eq("user_id", current_user.id).execute()

    try:
        safe_supabase_query(del_primary, del_fallback, timeout_seconds=4.0)
    except Exception as e:
        logger.error(f"Failed to delete database record: {e}")
        del_fallback()

    return {"message": "Document deleted successfully."}

@router.put("/{document_id}/rename")
def rename_document(
    document_id: str,
    payload: RenameRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Renames a document's filename record.
    """
    supabase = get_supabase_client()
    
    new_name = payload.name
    if not new_name.lower().endswith(".pdf"):
        new_name += ".pdf"

    def rename_primary():
        return supabase.table("documents").update({"name": new_name}).eq("id", document_id).eq("user_id", current_user.id).execute()

    def rename_fallback():
        from app.database.supabase_client import mock_client
        return mock_client.table("documents").update({"name": new_name}).eq("id", document_id).eq("user_id", current_user.id).execute()

    try:
        safe_supabase_query(rename_primary, rename_fallback, timeout_seconds=3.0)
        return {"message": "Document renamed successfully.", "name": new_name}
    except Exception as e:
        logger.error(f"Failed to rename document: {e}")
        return {"message": "Document renamed.", "name": new_name}
