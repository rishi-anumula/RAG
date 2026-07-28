import os
import shutil
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase_client
from app.services.pdf_service import pdf_service
from app.embeddings.embedder import embedding_service
from app.vectorstore.supabase_vector_client import add_document_chunks, delete_document_chunks

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# Max PDF Size: 100 MB
MAX_FILE_SIZE = 100 * 1024 * 1024

class ProcessRequest(BaseModel):
    document_id: str

class RenameRequest(BaseModel):
    name: str

def async_process_document(document_id: str, file_path: str, filename: str, user_id: str):
    """
    Background worker function that extracts text, splits it into chunks,
    generates embeddings, and indexes them into ChromaDB.
    """
    supabase = get_supabase_client()
    logger.info(f"Starting background indexing task for document {document_id}")
    
    try:
        # 1. Update status in DB to processing
        supabase.table("documents").update({"status": "processing"}).eq("id", document_id).execute()
        
        # 2. Extract and chunk text
        chunks_data = pdf_service.extract_and_chunk(file_path)
        if not chunks_data:
            raise ValueError("No text could be extracted from this PDF. It might be image-only or corrupted.")
            
        chunks = [c["text"] for c in chunks_data]
        pages = [c["page"] for c in chunks_data]
        chunk_indices = [c["chunk_index"] for c in chunks_data]
        
        # 3. Generate embeddings
        embeddings = embedding_service.get_embeddings(chunks)
        
        # 4. Store in ChromaDB
        success = add_document_chunks(
            user_id=user_id,
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings,
            start_page=pages,
            chunk_indices=chunk_indices
        )
        
        if not success:
            raise RuntimeError("ChromaDB ingestion failed.")
            
        # 5. Update status in DB to processed
        supabase.table("documents").update({
            "status": "processed",
            "error_message": None
        }).eq("id", document_id).execute()
        
        logger.info(f"Successfully finished background indexing for document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)
        supabase.table("documents").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", document_id).execute()

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user)
):
    """
    Upload a PDF document. Saves it locally, uploads to Supabase storage,
    registers metadata in DB, and automatically queues vector indexing.
    """
    logger.info(f"Uploading file '{file.filename}' for user {current_user.id}")
    
    # Validation: Allowed document extensions
    allowed_exts = {".pdf", ".txt", ".md", ".csv", ".json", ".doc", ".docx", ".log"}
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Supported formats are PDF, TXT, MD, CSV, JSON, and DOCX."
        )
        
    # Read size to validate
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large. Maximum allowed size is 100MB."
        )
        
    # Reset seek pointer
    await file.seek(0)
    
    supabase = get_supabase_client()
    
    # Duplicate Detection & Auto-naming
    filename = file.filename
    existing_check = supabase.table("documents").select("id").eq("user_id", current_user.id).eq("name", filename).execute()
    if existing_check.data and len(existing_check.data) > 0:
        base_name, ext = os.path.splitext(file.filename)
        timestamp = time.strftime("%H%M%S")
        filename = f"{base_name}_{timestamp}{ext}"

    # Make local upload directory path
    user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    local_file_path = os.path.join(user_upload_dir, filename)
    
    # Save file locally
    try:
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        logger.error(f"Failed to write file locally: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save file on backend server storage."
        )

    # Upload to Supabase Storage
    storage_path = f"{current_user.id}/{filename}"
    try:
        bucket = supabase.storage.from_("pdfs")
        bucket.upload(path=storage_path, file=file_bytes, file_options={"content-type": "application/pdf"})
    except Exception as e:
        logger.warning(f"Failed to upload document to Supabase storage: {e}")
        pass
        
    # Insert metadata into Database
    try:
        db_insert = supabase.table("documents").insert({
            "user_id": current_user.id,
            "name": filename,
            "size": file_size,
            "status": "processing",
            "storage_path": storage_path
        }).execute()
        
        if not db_insert.data:
            raise RuntimeError("Database entry creation failed.")
            
        doc_record = db_insert.data[0]
        logger.info(f"Document registered in DB: {doc_record['id']}")
        
        # Queue automatic background indexing
        background_tasks.add_task(
            async_process_document,
            document_id=doc_record["id"],
            file_path=local_file_path,
            filename=filename,
            user_id=current_user.id
        )
        
        return doc_record
    except Exception as e:
        logger.error(f"Database insertion failed: {e}", exc_info=True)
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database registration failed: {str(e)}"
        )

@router.get("", response_model=List[dict])
def list_documents(current_user: Any = Depends(get_current_user)):
    """
    Get all document metadata records for the current user.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table("documents").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve documents list.")

@router.get("/{document_id}/output")
def get_document_output(
    document_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Get detailed output, page chunks, vector info, and extracted content for a specific document.
    """
    supabase = get_supabase_client()
    
    db_check = supabase.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute()
    if not db_check.data:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    doc_record = db_check.data[0]
    chunks_res = supabase.table("document_chunks").select("*").eq("document_id", document_id).eq("user_id", current_user.id).execute()
    chunks = chunks_res.data or []
    
    if not chunks:
        user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
        local_file_path = os.path.join(user_upload_dir, doc_record["name"])
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
            except Exception as e:
                logger.warning(f"Could not extract preview text: {e}")

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
    
    # Verify ownership
    db_check = supabase.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute()
    if not db_check.data:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    doc_record = db_check.data[0]
    
    # 1. Delete from ChromaDB vector store
    delete_document_chunks(user_id=current_user.id, document_id=document_id)
    
    # 2. Delete local file cache
    user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
    local_file_path = os.path.join(user_upload_dir, doc_record["name"])
    if os.path.exists(local_file_path):
        try:
            os.remove(local_file_path)
            logger.info(f"Deleted local file cache: {local_file_path}")
        except Exception as e:
            logger.warning(f"Could not delete local file cache: {e}")

    # 3. Delete from Supabase Storage
    try:
        bucket = supabase.storage.from_("pdfs")
        bucket.remove([doc_record["storage_path"]])
        logger.info(f"Deleted file from Supabase storage: {doc_record['storage_path']}")
    except Exception as e:
        logger.warning(f"Could not delete file from Supabase storage: {e}")

    # 4. Delete from Database
    try:
        supabase.table("documents").delete().eq("id", document_id).execute()
        logger.info(f"Deleted document database entry for {document_id}")
    except Exception as e:
        logger.error(f"Failed to delete database record: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document from database.")

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
    
    # Verify ownership
    db_check = supabase.table("documents").select("*").eq("id", document_id).eq("user_id", current_user.id).execute()
    if not db_check.data:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    # Standardize name extension
    new_name = payload.name
    if not new_name.lower().endswith(".pdf"):
        new_name += ".pdf"
        
    try:
        supabase.table("documents").update({"name": new_name}).eq("id", document_id).execute()
        return {"message": "Document renamed successfully.", "name": new_name}
    except Exception as e:
        logger.error(f"Failed to rename document: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename document.")
