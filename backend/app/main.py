import sys
import os
import socket
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import get_logger
from app.embeddings.embedder import embedding_service
from app.api.endpoints import auth, documents, chat, dashboard, health
from app.core.errors import is_connection_error
from app.database.supabase_client import get_supabase_client

# Reconfigure stdout/stderr to support Unicode characters on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logger = get_logger(__name__)

def validate_startup_config():
    print("\nRunning startup checks...")
    errors = []
    
    # 1. Supabase URL
    if settings.SUPABASE_URL:
        print(f"✓ Supabase URL configured: {settings.SUPABASE_URL}")
    else:
        print("⚠ SUPABASE_URL missing: local SQLite mock active.")
        
    # 2. Gemini API
    if not settings.GOOGLE_API_KEY:
        print("✗ Gemini API Loaded: MISSING")
        errors.append("GOOGLE_API_KEY environment variable is missing or empty.")
    else:
        print("✓ Gemini API Loaded")
        
    # 3. Supabase Vector Store Connection
    try:
        supabase = get_supabase_client()
        supabase.table("document_chunks").select("id").limit(1).execute()
        print("✓ Supabase Vector Store Connected")
    except Exception as e:
        print(f"✗ Supabase Vector Store Connected: {e}")
        errors.append(f"Failed to connect to Supabase Vector Store: {e}")
        
    # 4. Upload Folder
    if not settings.UPLOAD_FOLDER:
        print("✗ Upload Folder Ready: MISSING")
        errors.append("UPLOAD_FOLDER settings variable is missing or empty.")
    else:
        try:
            os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
            # Test write permissions
            test_file = os.path.join(settings.UPLOAD_FOLDER, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print("✓ Upload Folder Ready")
        except Exception as e:
            print(f"✗ Upload Folder Ready: {e}")
            errors.append(f"Upload folder '{settings.UPLOAD_FOLDER}' is not writeable: {e}")
            
    # Validate other required credentials
    if not settings.SECRET_KEY:
        errors.append("SECRET_KEY environment variable is missing or empty.")
        
    if errors:
        print("\nCRITICAL: FastAPI server configuration warnings/errors:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease check your .env file and environment variables configuration on Render.\n")
        logger.error(f"Startup configuration warnings: {errors}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the application.
    Optimizes performance by pre-loading models.
    """
    logger.info("Starting up FastAPI application...")
    # Validate startup configuration and print checklists
    validate_startup_config()
    
    try:
        # Pre-load sentence transformers model to avoid request latency
        embedding_service.load_model()
        logger.info("All model services preloaded successfully.")
    except Exception as e:
        logger.critical(f"Startup check failed: {e}", exc_info=True)
    yield
    logger.info("Shutting down FastAPI application...")

# Initialize FastAPI App
app = FastAPI(
    title="AI Knowledge Base Search RAG API",
    description="Backend APIs for PDF processing, vector indexing, and generative AI chat",
    version="1.0.0",
    lifespan=lifespan
)

# Exception handlers to format connection/DNS errors into clean message
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if is_connection_error(exc):
        logger.error(f"Intercepted connection error in HTTP exception: {exc.detail}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Unable to connect to Supabase. Please verify your SUPABASE_URL, internet connection, and environment variables."}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(httpx.ConnectError)
async def httpx_connect_error_handler(request: Request, exc: httpx.ConnectError):
    logger.error(f"Intercepted unhandled httpx connection error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Unable to connect to Supabase. Please verify your SUPABASE_URL, internet connection, and environment variables."}
    )

@app.exception_handler(socket.gaierror)
async def socket_gaierror_handler(request: Request, exc: socket.gaierror):
    logger.error(f"Intercepted unhandled socket resolution error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Unable to connect to Supabase. Please verify your SUPABASE_URL, internet connection, and environment variables."}
    )

from fastapi import FastAPI, Request, HTTPException, status, APIRouter

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if hasattr(settings, "FRONTEND_URL") and settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|https://.*\.netlify\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers under both direct paths (e.g., /auth) and /api prefix (e.g., /api/auth)
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(health.router)

app.include_router(api_router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
app.include_router(health.router)

@app.get("/")
@app.get("/api")
@app.get("/api/")
def read_root():
    return {
        "title": "AI Knowledge Base Search RAG API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server directly...")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
