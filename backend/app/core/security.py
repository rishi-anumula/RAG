import json
import base64
from pydantic import BaseModel
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class MockUser(BaseModel):
    id: str = "00000000-0000-0000-0000-000000000000"
    email: str = "guest@example.com"

security = HTTPBearer(auto_error=False)

def decode_jwt_unverified(token: str) -> dict:
    """
    Decodes the payload of a JWT without verifying signature (for dependency user resolution).
    """
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload_b64 = parts[1]
            # Add padding if necessary
            padding = len(payload_b64) % 4
            if padding:
                payload_b64 += "=" * (4 - padding)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes)
    except Exception as e:
        logger.debug(f"Failed to decode JWT payload: {e}")
    return {}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> MockUser:
    """
    Extracts user_id and email from bearer token if present (supporting real Supabase JWTs & mock tokens),
    otherwise defaults to guest user.
    """
    if credentials:
        token = credentials.credentials
        if token:
            # 1. Check if mock token format: "user_id:email"
            if ":" in token:
                try:
                    user_id, email = token.split(":", 1)
                    return MockUser(id=user_id, email=email)
                except Exception as e:
                    logger.warning(f"Failed to parse mock credentials token: {e}")
            
            # 2. Try parsing as JWT token
            payload = decode_jwt_unverified(token)
            if payload:
                user_id = payload.get("sub") or payload.get("user_id")
                email = payload.get("email", "user@example.com")
                if user_id:
                    return MockUser(id=user_id, email=email)

    return MockUser()

