from pydantic import BaseModel
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class MockUser(BaseModel):
    id: str = "00000000-0000-0000-0000-000000000000"
    email: str = "guest@example.com"

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> MockUser:
    """
    Mock dependency that extracts user_id and email from bearer token if present,
    otherwise defaults to a guest user.
    """
    if credentials:
        token = credentials.credentials
        if token and ":" in token:
            try:
                user_id, email = token.split(":", 1)
                return MockUser(id=user_id, email=email)
            except Exception as e:
                logger.warning(f"Failed to parse mock credentials token: {e}")
    return MockUser()
