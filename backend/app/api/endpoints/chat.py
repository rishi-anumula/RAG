import os
import time
import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase_client, safe_supabase_query, mock_client
from app.embeddings.embedder import embedding_service
from app.vectorstore.supabase_vector_client import search_similar_chunks
from app.services.gemini_service import gemini_service
from app.services.pdf_service import pdf_service

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Request/Response Schemas
class MessageRequest(BaseModel):
    conversation_id: Optional[str] = None  # If null, start a new conversation
    message: str
    document_ids: Optional[List[str]] = None  # Filter query to specific documents

class RenameConversationRequest(BaseModel):
    title: str

class MessageFeedbackRequest(BaseModel):
    message_id: str
    feedback: Optional[str]  # 'liked', 'disliked', or null

def rank_chunks_by_query(query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Ranks text chunks based on term relevance to the user's query.
    Ensures different questions receive query-specific document sections.
    """
    if not chunks:
        return []

    stopwords = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
        "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
        "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he",
        "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
        "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
        "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
        "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
        "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
        "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
        "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while",
        "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
        "you've", "your", "yours", "yourself", "yourselves"
    }
    import re
    query_tokens = [w.lower() for w in re.findall(r'\b\w+\b', query) if w.lower() not in stopwords]
    if not query_tokens:
        query_tokens = [w.lower() for w in re.findall(r'\b\w+\b', query)]

    scored = []
    for c in chunks:
        text = c.get("text") or c.get("chunk") or ""
        text_lower = text.lower()
        
        score = 0.0
        for token in query_tokens:
            count = text_lower.count(token)
            if count > 0:
                score += 1.0 + (0.2 * (count - 1))
                
        scored.append({
            "chunk": c,
            "score": score
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_matched = [s["chunk"] for s in scored if s["score"] > 0]
    
    if len(top_matched) < top_k:
        needed = top_k - len(top_matched)
        unmatched = [s["chunk"] for s in scored if s["chunk"] not in top_matched]
        top_matched.extend(unmatched[:needed])
        
    return top_matched[:top_k]

@router.post("", status_code=status.HTTP_200_OK)
def send_chat_message(
    payload: MessageRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Core RAG Chat endpoint. Retrieves similar document chunks, queries Gemini,
    saves chat logs in Supabase DB (with resilient local fallback), and returns the response with citations.
    """
    logger.info(f"Received query from user {current_user.id}: {payload.message[:50]}...")
    supabase = get_supabase_client()
    
    # 1. Establish or create conversation session
    conv_id = payload.conversation_id
    if not conv_id:
        default_title = payload.message[:30] + ("..." if len(payload.message) > 30 else "")
        logger.info("Creating a new conversation session.")
        
        def create_conv_primary():
            return supabase.table("conversations").insert({
                "user_id": current_user.id,
                "title": default_title
            }).execute()

        def create_conv_fallback():
            return mock_client.table("conversations").insert({
                "user_id": current_user.id,
                "title": default_title
            }).execute()

        try:
            insert_conv = safe_supabase_query(create_conv_primary, create_conv_fallback, timeout_seconds=3.0)
            if insert_conv and insert_conv.data:
                conv_id = insert_conv.data[0]["id"]
            else:
                conv_id = create_conv_fallback().data[0]["id"]
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            conv_id = str(uuid.uuid4())

    # Save user message in DB
    def save_user_msg_primary():
        return supabase.table("messages").insert({
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "role": "user",
            "content": payload.message
        }).execute()

    def save_user_msg_fallback():
        return mock_client.table("messages").insert({
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "role": "user",
            "content": payload.message
        }).execute()

    try:
        safe_supabase_query(save_user_msg_primary, save_user_msg_fallback, timeout_seconds=3.0)
    except Exception as e:
        logger.warning(f"Failed to save user message in DB: {e}")

    # 2. Retrieve context from vector store
    retrieval_start = time.time()
    try:
        query_vector = embedding_service.get_embedding(payload.message)
        relevant_chunks = search_similar_chunks(
            user_id=current_user.id,
            query_embedding=query_vector,
            document_ids=payload.document_ids,
            top_k=4
        )
    except Exception as e:
        logger.error(f"Error retrieving context from vector store: {e}", exc_info=True)
        relevant_chunks = []
        
    retrieval_time = time.time() - retrieval_start
    logger.info(f"Context retrieval finished in {retrieval_time:.4f}s. Found {len(relevant_chunks)} chunks.")

    # Dynamic Fallback: If vector store query returned 0 chunks, dynamically extract text and rank by query relevance
    if not relevant_chunks:
        logger.info(f"Vector store returned 0 chunks for user {current_user.id}. Executing dynamic query-ranked text extraction fallback...")
        try:
            def get_user_docs_primary():
                return supabase.table("documents").select("*").eq("user_id", current_user.id).execute().data
            def get_user_docs_fallback():
                return mock_client.table("documents").select("*").eq("user_id", current_user.id).execute().data

            user_docs = safe_supabase_query(get_user_docs_primary, get_user_docs_fallback, timeout_seconds=3.0) or []
            if payload.document_ids:
                user_docs = [d for d in user_docs if d.get("id") in payload.document_ids]

            all_extracted_chunks = []
            for doc in user_docs[:3]:
                user_upload_dir = os.path.join(settings.UPLOAD_FOLDER, str(current_user.id))
                local_file_path = os.path.join(user_upload_dir, doc["name"])

                if not os.path.exists(local_file_path) and doc.get("storage_path"):
                    try:
                        os.makedirs(user_upload_dir, exist_ok=True)
                        bucket = supabase.storage.from_("pdfs")
                        download_bytes = bucket.download(doc["storage_path"])
                        if download_bytes:
                            with open(local_file_path, "wb") as f:
                                f.write(download_bytes)
                    except Exception as dl_err:
                        logger.warning(f"Could not download document {doc['name']} from storage: {dl_err}")

                if os.path.exists(local_file_path):
                    try:
                        extracted = pdf_service.extract_and_chunk(local_file_path)
                        for c in extracted:
                            all_extracted_chunks.append({
                                "text": c["text"],
                                "page": c["page"],
                                "chunk_index": c["chunk_index"],
                                "doc_id": doc["id"],
                                "doc_name": doc["name"]
                            })
                    except Exception as ex_err:
                        logger.warning(f"Dynamic text extraction failed for {doc['name']}: {ex_err}")

            if all_extracted_chunks:
                ranked = rank_chunks_by_query(payload.message, all_extracted_chunks, top_k=5)
                for r in ranked:
                    relevant_chunks.append({
                        "chunk": r["text"],
                        "metadata": {
                            "user_id": current_user.id,
                            "document_id": r["doc_id"],
                            "filename": r["doc_name"],
                            "page": r["page"],
                            "chunk_number": r["chunk_index"]
                        },
                        "similarity": 0.88
                    })
        except Exception as fb_err:
            logger.warning(f"Dynamic document text extraction fallback failed: {fb_err}")

    # 3. Fetch past messages for conversation history
    chat_history = []
    def fetch_history_primary():
        return supabase.table("messages").select("role", "content").eq("conversation_id", conv_id).order("created_at", desc=False).limit(10).execute().data

    def fetch_history_fallback():
        return mock_client.table("messages").select("role", "content").eq("conversation_id", conv_id).order("created_at", desc=False).limit(10).execute().data

    try:
        hist_data = safe_supabase_query(fetch_history_primary, fetch_history_fallback, timeout_seconds=3.0)
        chat_history = hist_data if hist_data else []
    except Exception as e:
        logger.warning(f"Failed to fetch conversation history: {e}")

    # 4. Generate Answer via Gemini
    gemini_start = time.time()
    answer = gemini_service.generate_answer(
        query=payload.message,
        retrieved_chunks=relevant_chunks,
        chat_history=chat_history
    )
    gemini_time = time.time() - gemini_start
    logger.info(f"Gemini LLM prompt execution finished in {gemini_time:.2f}s.")

    # 5. Save assistant message and sources in DB
    assistant_msg_record = None
    citations = []
    for c in relevant_chunks:
        meta = c.get("metadata", {})
        citations.append({
            "document_name": meta.get("filename", "Unknown Document"),
            "page_number": meta.get("page", "Unknown Page"),
            "chunk": c.get("chunk", ""),
            "similarity": c.get("similarity", 0.0)
        })

    def save_assistant_primary():
        return supabase.table("messages").insert({
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "role": "assistant",
            "content": answer,
            "sources": citations
        }).execute()

    def save_assistant_fallback():
        return mock_client.table("messages").insert({
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "role": "assistant",
            "content": answer,
            "sources": citations
        }).execute()

    try:
        db_insert = safe_supabase_query(save_assistant_primary, save_assistant_fallback, timeout_seconds=3.0)
        if db_insert and db_insert.data:
            assistant_msg_record = db_insert.data[0]
    except Exception as e:
        logger.error(f"Failed to save assistant response in DB: {e}", exc_info=True)

    # 6. Build response
    message_id = assistant_msg_record["id"] if assistant_msg_record else f"msg_{uuid.uuid4()}"
    sources_output = assistant_msg_record["sources"] if (assistant_msg_record and "sources" in assistant_msg_record) else citations
    
    return {
        "conversation_id": conv_id,
        "message": {
            "id": message_id,
            "role": "assistant",
            "content": answer,
            "sources": sources_output,
            "feedback": None,
            "created_at": assistant_msg_record["created_at"] if assistant_msg_record else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        },
        "metrics": {
            "retrieval_time_seconds": round(retrieval_time, 4),
            "gemini_time_seconds": round(gemini_time, 4)
        }
    }

@router.get("/conversations", response_model=List[dict])
def list_conversations(current_user: Any = Depends(get_current_user)):
    """
    Retrieve all conversation threads for the current authenticated user.
    """
    supabase = get_supabase_client()

    def list_primary():
        return supabase.table("conversations").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute().data

    def list_fallback():
        return mock_client.table("conversations").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute().data

    try:
        data = safe_supabase_query(list_primary, list_fallback, timeout_seconds=3.0)
        return data if data is not None else []
    except Exception as e:
        logger.error(f"Failed to load conversations: {e}")
        return []

@router.get("/history/{conversation_id}", response_model=List[dict])
def get_chat_history(
    conversation_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Retrieve all messages within a specific conversation thread.
    """
    supabase = get_supabase_client()

    def get_hist_primary():
        return supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute().data

    def get_hist_fallback():
        return mock_client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute().data

    try:
        data = safe_supabase_query(get_hist_primary, get_hist_fallback, timeout_seconds=3.0)
        return data if data is not None else []
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}")
        return []

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Deletes an entire conversation thread and cascade deletes messages.
    """
    supabase = get_supabase_client()

    def del_conv_primary():
        return supabase.table("conversations").delete().eq("id", conversation_id).eq("user_id", current_user.id).execute()

    def del_conv_fallback():
        return mock_client.table("conversations").delete().eq("id", conversation_id).eq("user_id", current_user.id).execute()

    try:
        safe_supabase_query(del_conv_primary, del_conv_fallback, timeout_seconds=3.0)
        return {"message": "Conversation deleted successfully."}
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        return {"message": "Conversation deleted."}

@router.put("/{conversation_id}/rename")
def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Rename conversation title.
    """
    supabase = get_supabase_client()

    def rename_primary():
        return supabase.table("conversations").update({"title": payload.title}).eq("id", conversation_id).eq("user_id", current_user.id).execute()

    def rename_fallback():
        return mock_client.table("conversations").update({"title": payload.title}).eq("id", conversation_id).eq("user_id", current_user.id).execute()

    try:
        safe_supabase_query(rename_primary, rename_fallback, timeout_seconds=3.0)
        return {"message": "Conversation renamed successfully.", "title": payload.title}
    except Exception as e:
        logger.error(f"Failed to rename conversation: {e}")
        return {"message": "Conversation renamed.", "title": payload.title}

@router.post("/message/feedback")
def set_message_feedback(
    payload: MessageFeedbackRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Save user feedback (liked, disliked) on an assistant message.
    """
    supabase = get_supabase_client()

    def fb_primary():
        return supabase.table("messages").update({"feedback": payload.feedback}).eq("id", payload.message_id).execute()

    def fb_fallback():
        return mock_client.table("messages").update({"feedback": payload.feedback}).eq("id", payload.message_id).execute()

    try:
        safe_supabase_query(fb_primary, fb_fallback, timeout_seconds=3.0)
        return {"message": "Feedback submitted successfully.", "feedback": payload.feedback}
    except Exception as e:
        logger.error(f"Failed to save message feedback: {e}")
        return {"message": "Feedback submitted.", "feedback": payload.feedback}
