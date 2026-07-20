import socket
import httpx
from fastapi import HTTPException, status
from app.core.logging_config import get_logger

logger = get_logger(__name__)

def is_connection_error(e: Exception) -> bool:
    err_str = str(e).lower()
    if hasattr(e, "detail"):
        err_str += " " + str(getattr(e, "detail")).lower()
    return (
        isinstance(e, (httpx.ConnectError, socket.gaierror))
        or "getaddrinfo" in err_str
        or "connection" in err_str
        or "timeout" in err_str
        or "failed to establish a new connection" in err_str
        or "name or service not known" in err_str
    )

def handle_exception(e: Exception, custom_message: str = None):
    # Log the full exception with traceback to logs/app.log
    logger.error(f"Error caught: {e}", exc_info=True)
    
    if is_connection_error(e):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to Supabase. Please verify your SUPABASE_URL, internet connection, and environment variables."
        )
        
    if custom_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=custom_message
        )
        
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(e)
    )
