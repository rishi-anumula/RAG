from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.database.supabase_client import get_supabase_client
from app.core.logging_config import get_logger
from app.core.errors import handle_exception, is_connection_error

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Request/Response Schemas
class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: AuthRequest):
    """
    Registers a new user in Supabase Auth.
    """
    logger.info(f"Received signup request for: {payload.email}")
    supabase = get_supabase_client(use_service_role=False)
    try:
        response = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password
        })
        
        # Checking if registration generated user
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed. Please try again."
            )
            
        logger.info(f"Signup successful for user: {response.user.id}")
        
        # Format response
        session_data = None
        if response.session:
            session_data = {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at
            }
            
        return {
            "message": "User registered successfully. Please check your email for verification if enabled.",
            "user": {
                "id": response.user.id,
                "email": response.user.email
            },
            "session": session_data
        }
    except Exception as e:
        handle_exception(e)

@router.post("/login")
def login(payload: AuthRequest):
    """
    Authenticates a user using Supabase Auth.
    """
    logger.info(f"Received login request for: {payload.email}")
    supabase = get_supabase_client(use_service_role=False)
    try:
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed. No session returned."
            )
            
        logger.info(f"User logged in successfully: {response.user.id}")
        
        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at
            }
        }
    except Exception as e:
        if is_connection_error(e):
            handle_exception(e)
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    """
    Sends a password reset email using Supabase Auth.
    """
    logger.info(f"Received forgot password request for: {payload.email}")
    supabase = get_supabase_client(use_service_role=False)
    try:
        response = supabase.auth.reset_password_for_email(payload.email)
        logger.info(f"Password reset email sent to: {payload.email}")
        return {"message": "Password reset link sent successfully."}
    except Exception as e:
        handle_exception(e)

