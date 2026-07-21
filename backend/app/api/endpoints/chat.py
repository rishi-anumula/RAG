import time
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase_client
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
    saves chat logs in Supabase DB, and returns the response with citations.
    """
    logger.info(f"Received query from user {current_user.id}: {payload.message[:50]}...")
    supabase = get_supabase_client()
    
    # 1. Establish or create conversation
    conv_id = payload.conversation_id
    if not conv_id:
        try:
            # Create a default title derived from the query
            default_title = payload.message[:30] + ("..." if len(payload.message) > 30 else "")
            logger.info("Creating a new conversation session.")
            insert_conv = supabase.table("conversations").insert({
                "user_id": current_user.id,
                "title": default_title
            }).execute()
            if not insert_conv.data:
                raise RuntimeError("Failed to create conversation record.")
            conv_id = insert_conv.data[0]["id"]
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize chat session.")

    # Save user message in DB
    try:
        supabase.table("messages").insert({
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "role": "user",
            "content": payload.message
        }).execute()
    except Exception as e:
        logger.error(f"Failed to save user message in DB: {e}")
        # Continue with chat generation even if save fails, but log it

    # 2. Retrieve context from ChromaDB
    retrieval_start = time.time()
    try:
        # Generate embedding for user query
        query_vector = embedding_service.get_embedding(payload.message)
        
        # Search ChromaDB
        relevant_chunks = search_similar_chunks(
            user_id=current_user.id,
            query_embedding=query_vector,
            document_ids=payload.document_ids,
            top_k=5
        )
    except Exception as e:
        logger.error(f"Error retrieving context from ChromaDB: {e}", exc_info=True)
        relevant_chunks = []
        
    retrieval_time = time.time() - retrieval_start
    logger.info(f"Context retrieval finished in {retrieval_time:.4f}s. Found {len(relevant_chunks)} chunks.")

    # 3. Fetch past messages for history
    chat_history = []
    try:
        history_response = supabase.table("messages").select("role", "content").eq("conversation_id", conv_id).order("created_at", desc=False).limit(10).execute()
        chat_history = history_response.data if history_response.data else []
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
    try:
        # Save sources as a formatted JSON structure
        # Each source contains: doc_name, page, chunk_text, similarity
        citations = []
        for c in relevant_chunks:
            meta = c.get("metadata", {})
            citations.append({
                "document_name": meta.get("filename", "Unknown Document"),
                "page_number": meta.get("page", "Unknown Page"),
                "chunk": c.get("chunk", ""),
                "similarity": c.get("similarity", 0.0)
            })

        db_insert = supabase.table("messages").insert({
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "role": "assistant",
            "content": answer,
            "sources": citations
        }).execute()
        if db_insert.data:
            assistant_msg_record = db_insert.data[0]
    except Exception as e:
        logger.error(f"Failed to save assistant response in DB: {e}", exc_info=True)

    # 6. Build response
    message_id = assistant_msg_record["id"] if assistant_msg_record else "temp_id"
    sources_output = assistant_msg_record["sources"] if assistant_msg_record else []
    
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
    try:
        response = supabase.table("conversations").select("*").eq("user_id", current_user.id).order("updated_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to load conversations: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve chat conversations.")

@router.get("/history/{conversation_id}", response_model=List[dict])
def get_chat_history(
    conversation_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Retrieve all messages within a specific conversation thread.
    """
    supabase = get_supabase_client()
    try:
        # Check ownership
        conv_check = supabase.table("conversations").select("id").eq("id", conversation_id).eq("user_id", current_user.id).execute()
        if not conv_check.data:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
            
        messages_response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
        return messages_response.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}")
        raise HTTPException(status_code=500, detail="Could not load messages.")

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Deletes an entire conversation thread and cascade deletes messages.
    """
    supabase = get_supabase_client()
    try:
        # Check ownership
        conv_check = supabase.table("conversations").select("id").eq("id", conversation_id).eq("user_id", current_user.id).execute()
        if not conv_check.data:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

        supabase.table("conversations").delete().eq("id", conversation_id).execute()
        logger.info(f"Deleted conversation: {conversation_id}")
        return {"message": "Conversation deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail="Could not delete conversation.")

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
    try:
        # Check ownership
        conv_check = supabase.table("conversations").select("id").eq("id", conversation_id).eq("user_id", current_user.id).execute()
        if not conv_check.data:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
            
        supabase.table("conversations").update({"title": payload.title}).eq("id", conversation_id).execute()
        return {"message": "Conversation renamed successfully.", "title": payload.title}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename conversation: {e}")
        raise HTTPException(status_code=500, detail="Could not rename conversation.")

@router.post("/message/feedback")
def set_message_feedback(
    payload: MessageFeedbackRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Save user feedback (liked, disliked) on an assistant message.
    """
    supabase = get_supabase_client()
    try:
        # Check ownership of message via conversations join
        msg_check = supabase.table("messages").select("id, user_id").eq("id", payload.message_id).execute()
        if not msg_check.data:
            raise HTTPException(status_code=404, detail="Message not found.")
            
        record = msg_check.data[0]
        if record["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied.")
            
        supabase.table("messages").update({"feedback": payload.feedback}).eq("id", payload.message_id).execute()
        return {"message": "Feedback submitted successfully.", "feedback": payload.feedback}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save message feedback: {e}")
        raise HTTPException(status_code=500, detail="Could not update feedback.")
