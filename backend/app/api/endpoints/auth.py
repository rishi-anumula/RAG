from typing import Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from app.database.supabase_client import get_supabase_client, MockSupabaseClient
from app.core.logging_config import get_logger
from app.core.errors import handle_exception, is_connection_error
from app.core.security import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Request/Response Schemas
class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: AuthRequest):
    """
    Registers a new user in Supabase Auth using supabase.auth.sign_up.
    Returns HTTP 201 on success. Returns exact Supabase error messages if registration fails.
    """
    logger.info(f"Received signup request for: {payload.email}")
    supabase = get_supabase_client(use_service_role=False)
    
    try:
        response = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password
        })
        
        # Log full Supabase response for diagnostic transparency
        logger.info(
            f"Full Supabase signup response for {payload.email}: "
            f"user={getattr(response, 'user', None)}, "
            f"session={getattr(response, 'session', None)}"
        )

        user_obj = getattr(response, "user", None)
        if not response or not user_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed. Unable to create account."
            )

        session_obj = getattr(response, "session", None)
        session_data = None
        if session_obj:
            session_data = {
                "access_token": getattr(session_obj, "access_token", None),
                "refresh_token": getattr(session_obj, "refresh_token", None),
                "expires_in": getattr(session_obj, "expires_in", None),
                "expires_at": getattr(session_obj, "expires_at", None)
            }

        # Check if email confirmation is required by Supabase project settings
        if not session_data:
            message = "Account created successfully. Please verify your email."
        else:
            message = "Account created successfully."

        logger.info(f"Signup successful for user ID: {getattr(user_obj, 'id', 'unknown')}")

        return {
            "message": message,
            "user": {
                "id": getattr(user_obj, "id", None),
                "email": getattr(user_obj, "email", payload.email)
            },
            "session": session_data
        }

    except HTTPException:
        raise
    except Exception as e:
        if is_connection_error(e):
            handle_exception(e)

        # Extract exact Supabase error message
        err_msg = str(e)
        if hasattr(e, "message") and getattr(e, "message"):
            err_msg = str(getattr(e, "message"))
        elif hasattr(e, "detail") and getattr(e, "detail"):
            err_msg = str(getattr(e, "detail"))

        logger.error(f"Supabase signup failed for {payload.email}: {err_msg}", exc_info=True)

        status_code = status.HTTP_400_BAD_REQUEST
        if hasattr(e, "code") and isinstance(getattr(e, "code"), int):
            status_code = getattr(e, "code")
        elif hasattr(e, "status") and isinstance(getattr(e, "status"), int):
            status_code = getattr(e, "status")

        raise HTTPException(
            status_code=status_code,
            detail=err_msg
        )

@router.post("/login")
def login(payload: AuthRequest):
    """
    Authenticates a user using Supabase Auth with sign_in_with_password.
    Returns exact Supabase authentication errors on failure.
    """
    logger.info(f"Received login request for: {payload.email}")
    supabase = get_supabase_client(use_service_role=False)
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        # Log full Supabase response
        logger.info(
            f"Full Supabase login response for {payload.email}: "
            f"user={getattr(response, 'user', None)}, "
            f"session={getattr(response, 'session', None)}"
        )

        user_obj = getattr(response, "user", None)
        session_obj = getattr(response, "session", None)

        if not response or not session_obj or not user_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed. Invalid email or password."
            )

        logger.info(f"User logged in successfully: {user_obj.id}")

        return {
            "user": {
                "id": user_obj.id,
                "email": user_obj.email
            },
            "session": {
                "access_token": session_obj.access_token,
                "refresh_token": session_obj.refresh_token,
                "expires_in": session_obj.expires_in,
                "expires_at": session_obj.expires_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        if is_connection_error(e):
            handle_exception(e)

        # Extract exact Supabase error message
        err_msg = str(e)
        if hasattr(e, "message") and getattr(e, "message"):
            err_msg = str(getattr(e, "message"))
        elif hasattr(e, "detail") and getattr(e, "detail"):
            err_msg = str(getattr(e, "detail"))

        logger.error(f"Supabase login failed for {payload.email}: {err_msg}", exc_info=True)

        status_code = status.HTTP_401_UNAUTHORIZED
        if hasattr(e, "code") and isinstance(getattr(e, "code"), int):
            status_code = getattr(e, "code")
        elif hasattr(e, "status") and isinstance(getattr(e, "status"), int):
            status_code = getattr(e, "status")

        raise HTTPException(
            status_code=status_code,
            detail=err_msg
        )

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Updates the password for the current authenticated user.
    """
    logger.info(f"Received change password request for user: {current_user.id}")
    supabase = get_supabase_client(use_service_role=False)
    
    if isinstance(supabase, MockSupabaseClient):
        try:
            supabase.auth.update_password(
                user_id=current_user.id,
                email=current_user.email,
                current_pass=payload.current_password,
                new_pass=payload.new_password
            )
            return {"message": "Password updated successfully."}
        except Exception as e:
            logger.warning(f"Mock password update failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    else:
        try:
            try:
                supabase.auth.sign_in_with_password({
                    "email": current_user.email,
                    "password": payload.current_password
                })
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect."
                )
                
            supabase.auth.update_user({"password": payload.new_password})
            logger.info(f"Password updated successfully for user: {current_user.id}")
            return {"message": "Password updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            handle_exception(e)

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    """
    Sends a password reset email using Supabase Auth.
    """
    logger.info(f"Received forgot password request for: {payload.email}")
    supabase = get_supabase_client(use_service_role=False)
    try:
        supabase.auth.reset_password_for_email(payload.email)
        logger.info(f"Password reset email sent to: {payload.email}")
        return {"message": "Password reset link sent successfully."}
    except Exception as e:
        handle_exception(e)
