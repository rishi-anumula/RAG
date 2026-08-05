import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_signup_endpoint(mock_supabase_client):
    test_email = "test@example.com"
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
    test_email = "test@example.com"
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

def test_change_password_endpoint(mock_supabase_client):
    headers = {"Authorization": "Bearer 00000000-0000-0000-0000-000000000000:guest@example.com"}
    payload = {
        "current_password": "oldpassword123",
        "new_password": "newpassword123"
    }
    response = client.post("/auth/change-password", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Password updated successfully."}
