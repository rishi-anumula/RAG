import sys
import os

# Ensure the root directory and backend directory are in the Python search path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Set VERCEL environment variable flag
os.environ["VERCEL"] = "1"

# Import FastAPI application instance
from backend.app.main import app

# Export app for Vercel Serverless Function runtime
__all__ = ["app"]
