from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase_client
from app.core.errors import handle_exception, is_connection_error

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("")
def get_dashboard_metrics(current_user: Any = Depends(get_current_user)):
    """
    Retrieves summary statistics for the user dashboard.
    """
    supabase = get_supabase_client()
    try:
        # 1. Fetch all documents for count & size calculation
        docs_response = supabase.table("documents").select("id, name, size, status, created_at").eq("user_id", current_user.id).execute()
        documents = docs_response.data if docs_response.data else []
        
        total_pdfs = len(documents)
        total_size_bytes = sum(doc.get("size", 0) for doc in documents)
        
        # 2. Fetch conversations
        convs_response = supabase.table("conversations").select("id, title, updated_at").eq("user_id", current_user.id).order("updated_at", desc=True).execute()
        conversations = convs_response.data if convs_response.data else []
        total_conversations = len(conversations)

        # Sort documents to get 5 most recent uploads
        recent_uploads = sorted(documents, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        recent_chats = conversations[:5]
        
        return {
            "total_pdfs": total_pdfs,
            "total_conversations": total_conversations,
            "storage_usage_bytes": total_size_bytes,
            "recent_uploads": recent_uploads,
            "recent_chats": recent_chats
        }
    except Exception as e:
        if is_connection_error(e):
            handle_exception(e)
        logger.error(f"Failed to fetch dashboard metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not calculate dashboard metrics.")
