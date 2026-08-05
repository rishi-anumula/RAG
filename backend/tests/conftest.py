import sys
import os
from unittest.mock import MagicMock
import pytest

# Add backend app directory to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Mock environment configuration fields to prevent loading issues.
    """
    monkeypatch.setenv("SUPABASE_URL", "https://mock.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "mock-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "mock-service-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "mock-gemini-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("CHROMA_DB_PATH", "./test_chroma_db")
    monkeypatch.setenv("UPLOAD_FOLDER", "./test_uploads")

@pytest.fixture
def mock_supabase_client(monkeypatch):
    """
    Mock the Supabase database and authentication clients.
    """
    mock_client = MagicMock()
    
    # Mock auth responses
    mock_auth = MagicMock()
    mock_auth.sign_up.return_value = MagicMock(user=MagicMock(id="user_123", email="test@example.com"), session=None)
    mock_auth.sign_in_with_password.return_value = MagicMock(user=MagicMock(id="user_123", email="test@example.com"), session=MagicMock(access_token="jwt_123", expires_in=3600))
    mock_auth.get_user.return_value = MagicMock(user=MagicMock(id="user_123", email="test@example.com"))
    
    mock_client.auth = mock_auth
    
    # Mock DB query syntax
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "doc_123", "name": "test.pdf", "size": 1024, "status": "uploaded"}])
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    
    mock_client.table.return_value = mock_table
    
    monkeypatch.setattr("app.database.supabase_client.supabase_anon", mock_client)
    monkeypatch.setattr("app.database.supabase_client.supabase_service", mock_client)
    monkeypatch.setattr("app.database.supabase_client.get_supabase_client", lambda use_service_role=False: mock_client)
    monkeypatch.setattr("app.api.endpoints.auth.get_supabase_client", lambda use_service_role=False: mock_client)
    return mock_client
