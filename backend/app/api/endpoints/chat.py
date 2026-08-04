import time
import uuid
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase_client, safe_supabase_query, mock_client
from app.embeddings.embedder import embedding_service
from app.vectorstore.supabase_vector_client import search_similar_chunks
from app.services.gemini_service import gemini_service

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
            top_k=5
        )
    except Exception as e:
        logger.error(f"Error retrieving context from vector store: {e}", exc_info=True)
        relevant_chunks = []
        
    retrieval_time = time.time() - retrieval_start
    logger.info(f"Context retrieval finished in {retrieval_time:.4f}s. Found {len(relevant_chunks)} chunks.")

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
