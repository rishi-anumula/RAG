import os
import math
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase_client, MockSupabaseClient

logger = get_logger(__name__)

def add_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: List[str],
    embeddings: List[List[float]],
    start_page: List[int],
    chunk_indices: List[int]
) -> bool:
    """
    Inserts chunks, metadata, and generated vector embeddings into Supabase vector store (or local SQLite mock).
    """
    try:
        if not chunks:
            logger.warning("Empty chunks list passed to add_document_chunks.")
            return True

        supabase = get_supabase_client()
        
        # Prepare records
        records = []
        for i in range(len(chunks)):
            records.append({
                "document_id": document_id,
                "user_id": user_id,
                "filename": filename,
                "page_number": int(start_page[i]),
                "chunk_number": int(chunk_indices[i]),
                "content": chunks[i],
                "embedding": embeddings[i]
            })

        if isinstance(supabase, MockSupabaseClient):
            logger.info(f"Adding {len(chunks)} chunks to mock local SQLite document_chunks table.")
            conn = sqlite3.connect(supabase.db_path)
            cursor = conn.cursor()
            try:
                for r in records:
                    import uuid
                    chunk_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO document_chunks 
                        (id, document_id, user_id, filename, page_number, chunk_number, content, embedding, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk_id,
                            r["document_id"],
                            r["user_id"],
                            r["filename"],
                            r["page_number"],
                            r["chunk_number"],
                            r["content"],
                            json.dumps(r["embedding"]),
                            datetime.utcnow().isoformat() + "Z"
                        )
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            logger.info(f"Adding {len(chunks)} chunks for document {document_id} ({filename}) to Supabase pgvector table.")
            supabase.table("document_chunks").insert(records).execute()
            
        logger.info(f"Successfully added document {document_id} chunks to vector store.")
        return True
    except Exception as e:
        logger.error(f"Error adding chunks to vector store for doc {document_id}: {e}", exc_info=True)
        return False

def search_similar_chunks(
    user_id: str,
    query_embedding: List[float],
    document_ids: Optional[List[str]] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries the vector store for the top_k most similar chunks, filtered by user_id and optionally document_ids.
    Uses Python-based cosine similarity for mock client and match_document_chunks RPC for real Supabase pgvector.
    """
    try:
        supabase = get_supabase_client()
        
        if isinstance(supabase, MockSupabaseClient):
            logger.info(f"Querying local SQLite mock document_chunks table for user_id={user_id}")
            
            def cosine_similarity(v1, v2):
                dot_product = sum(x*y for x, y in zip(v1, v2))
                norm_v1 = math.sqrt(sum(x*x for x in v1))
                norm_v2 = math.sqrt(sum(x*x for x in v2))
                if norm_v1 == 0 or norm_v2 == 0:
                    return 0.0
                return dot_product / (norm_v1 * norm_v2)

            conn = sqlite3.connect(supabase.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                query = "SELECT * FROM document_chunks WHERE user_id = ?"
                params = [user_id]
                
                if document_ids and len(document_ids) > 0:
                    placeholders = ",".join(["?"] * len(document_ids))
                    query += f" AND document_id IN ({placeholders})"
                    params.extend(document_ids)
                    
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                results = []
                for r in rows:
                    row_dict = dict(r)
                    emb = json.loads(row_dict["embedding"])
                    sim = cosine_similarity(query_embedding, emb)
                    results.append({
                        "chunk": row_dict["content"],
                        "metadata": {
                            "user_id": row_dict["user_id"],
                            "document_id": row_dict["document_id"],
                            "filename": row_dict["filename"],
                            "page": row_dict["page_number"],
                            "chunk_number": row_dict["chunk_number"]
                        },
                        "similarity": round(max(0.0, min(1.0, sim)), 4)
                    })
                
                # Sort descending by similarity
                results.sort(key=lambda x: x["similarity"], reverse=True)
                return results[:top_k]
            finally:
                conn.close()
        else:
            logger.info(f"Querying Supabase pgvector database via RPC for user_id={user_id}")
            rpc_params = {
                "query_embedding": query_embedding,
                "match_threshold": 0.0,
                "match_count": top_k,
                "filter_user_id": user_id
            }
            if document_ids:
                rpc_params["filter_document_ids"] = document_ids
                
            response = supabase.rpc("match_document_chunks", rpc_params).execute()
            
            results = []
            if response.data:
                for item in response.data:
                    results.append({
                        "chunk": item["content"],
                        "metadata": {
                            "user_id": item["user_id"],
                            "document_id": item["document_id"],
                            "filename": item["filename"],
                            "page": item["page_number"],
                            "chunk_number": item["chunk_number"]
                        },
                        "similarity": round(item["similarity"], 4)
                    })
            return results
    except Exception as e:
        logger.error(f"Error searching vector store: {e}", exc_info=True)
        return []

def delete_document_chunks(user_id: str, document_id: str) -> bool:
    """
    Deletes all vector chunks belonging to a document.
    """
    try:
        supabase = get_supabase_client()
        
        if isinstance(supabase, MockSupabaseClient):
            logger.info(f"Deleting chunks for document {document_id} of user {user_id} from SQLite mock database.")
            conn = sqlite3.connect(supabase.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "DELETE FROM document_chunks WHERE user_id = ? AND document_id = ?",
                    (user_id, document_id)
                )
                conn.commit()
            finally:
                conn.close()
        else:
            logger.info(f"Deleting chunks for document {document_id} of user {user_id} from Supabase table.")
            supabase.table("document_chunks").delete().eq("user_id", user_id).eq("document_id", document_id).execute()
            
        logger.info(f"Successfully deleted document {document_id} chunks from vector store.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete document {document_id} chunks: {e}", exc_info=True)
        return False
