import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_signup_endpoint(mock_supabase_client):
    test_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": test_email,
        "password": "securepassword123"
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == test_email
    assert "message" in data

def test_login_endpoint(mock_supabase_client):
    test_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    signup_payload = {
        "email": test_email,
        "password": "securepassword123"
    }
    # First sign up
    client.post("/auth/signup", json=signup_payload)

    # Now login
    login_payload = {
        "email": test_email,
        "password": "securepassword123"
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == test_email
    assert "session" in data
    assert "access_token" in data["session"]

def test_login_invalid_credentials(mock_supabase_client):
    payload = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()

def test_change_password_endpoint(mock_supabase_client):
    headers = {"Authorization": "Bearer 00000000-0000-0000-0000-000000000000:guest@example.com"}
    payload = {
        "current_password": "oldpassword123",
        "new_password": "newpassword123"
    }
    response = client.post("/auth/change-password", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Password updated successfully."}

def test_change_password_invalid_current(mock_supabase_client):
    headers = {"Authorization": "Bearer 00000000-0000-0000-0000-000000000000:test_user@example.com"}
    from app.database.supabase_client import get_supabase_client
    supabase = get_supabase_client()
    if hasattr(supabase, "auth") and hasattr(supabase.auth, "update_password"):
        supabase.auth.update_password("test_user_id", "test_user@example.com", "", "correct_pass")
        
        payload = {
            "current_password": "wrong_pass",
            "new_password": "new_pass"
        }
        res = client.post("/auth/change-password", json=payload, headers=headers)
        assert res.status_code == 400
        assert "incorrect" in res.json()["detail"].lower()
