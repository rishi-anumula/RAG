import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
    # First set a known password in MockAuth sqlite db
    from app.database.supabase_client import get_supabase_client
    supabase = get_supabase_client()
    if hasattr(supabase, "auth") and hasattr(supabase.auth, "update_password"):
        supabase.auth.update_password("test_user_id", "test_user@example.com", "", "correct_pass")
        
        # Request with incorrect password
        payload = {
            "current_password": "wrong_pass",
            "new_password": "new_pass"
        }
        res = client.post("/auth/change-password", json=payload, headers=headers)
        assert res.status_code == 400
        assert "incorrect" in res.json()["detail"].lower()
