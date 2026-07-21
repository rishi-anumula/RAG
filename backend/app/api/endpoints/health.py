import socket
import httpx
from urllib.parse import urlparse
from fastapi import APIRouter
from app.core.config import settings
from app.database.supabase_client import get_supabase_client

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check():
    """
    Returns the connectivity status of Supabase, Gemini, and ChromaDB.
    """
    # 1. Supabase connection check (Probes SQLite mock database client)
    supabase_status = "disconnected"
    try:
        client = get_supabase_client()
        client.table("documents").select("id").limit(1).execute()
        supabase_status = "connected"
    except Exception:
        supabase_status = "disconnected"

    # 2. Gemini connection check
    gemini_status = "disconnected"
    try:
        socket.gethostbyname("generativeai.googleapis.com")
        gemini_status = "connected"
    except Exception:
        gemini_status = "disconnected"

    # 3. Vector Database connection check (labeled as chromadb for compatibility)
    chromadb_status = "disconnected"
    try:
        client = get_supabase_client()
        client.table("document_chunks").select("id").limit(1).execute()
        chromadb_status = "connected"
    except Exception:
        chromadb_status = "disconnected"

    # Status is 'ok' only if all services are connected
    status_val = "ok" if (supabase_status == "connected" and gemini_status == "connected" and chromadb_status == "connected") else "error"

    return {
        "status": status_val,
        "supabase": supabase_status,
        "gemini": gemini_status,
        "chromadb": chromadb_status
    }

@router.get("/debug/config")
def debug_config():
    """
    Returns masked configuration details, network status, DNS state, and hostname.
    """
    # 1. Mask Supabase URL
    parsed = urlparse(settings.SUPABASE_URL)
    masked_url = ""
    if parsed.scheme and parsed.netloc:
        netloc = parsed.netloc
        if len(netloc) > 6:
            masked_netloc = netloc[:2] + "*" * (len(netloc) - 5) + netloc[-3:]
        else:
            masked_netloc = "***"
        masked_url = f"{parsed.scheme}://{masked_netloc}"
    else:
        masked_url = "Invalid/Empty URL"

    # 2. Environment loaded status
    env_loaded = {
        "SUPABASE_URL_present": bool(settings.SUPABASE_URL),
        "SUPABASE_ANON_KEY_present": bool(settings.SUPABASE_ANON_KEY),
        "SUPABASE_SERVICE_ROLE_KEY_present": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
        "GOOGLE_API_KEY_present": bool(settings.GOOGLE_API_KEY),
        "SECRET_KEY_present": bool(settings.SECRET_KEY),
    }

    # 3. Hostname
    hostname = socket.gethostname()

    # 4. DNS Status
    dns_status = {}
    for host in ["supabase.co", "generativeai.googleapis.com", "google.com"]:
        try:
            socket.gethostbyname(host)
            dns_status[host] = "resolved"
        except Exception as e:
            dns_status[host] = f"failed: {e}"

    # 5. Internet Connectivity
    internet_conn = "disconnected"
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get("http://clients3.google.com/generate_204")
            if resp.status_code == 204:
                internet_conn = "connected"
    except Exception as e:
        internet_conn = f"failed: {e}"

    # 6. Vector Database Status (labeled as chroma_status for compatibility)
    chroma_status = "disconnected"
    try:
        client = get_supabase_client()
        client.table("document_chunks").select("id").limit(1).execute()
        chroma_status = "connected"
    except Exception as e:
        chroma_status = f"failed: {e}"

    return {
        "supabase_url_masked": masked_url,
        "environment_loaded": env_loaded,
        "backend_hostname": hostname,
        "dns_status": dns_status,
        "internet_connectivity": internet_conn,
        "chromadb_status": chroma_status
    }
