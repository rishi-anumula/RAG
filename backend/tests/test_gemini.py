import pytest
from unittest.mock import patch, MagicMock
from app.services.gemini_service import GeminiService

def test_gemini_prompt_synthesis():
    """
    Validates that context citation parameters are correctly aggregated into
    the final prompt string sent to the Gemini API.
    """
    service = GeminiService()
    service.initialized = True  # Mock connection state
    
    mock_chunks = [
        {
            "chunk": "FastAPI is a modern, fast (high-performance), web framework for building APIs.",
            "metadata": {"filename": "fastapi_manual.pdf", "page": 2},
            "similarity": 0.9421
        },
        {
            "chunk": "Uvicorn is an ASGI web server implementation for Python.",
            "metadata": {"filename": "uvicorn_docs.pdf", "page": 12},
            "similarity": 0.8512
        }
    ]
    
    query = "What is FastAPI?"
    
    # Mock the GenerativeModel class to prevent network API calls
    with patch("google.generativeai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="Mocked Answer referencing fastapi_manual.pdf p.2")
        mock_model_class.return_value = mock_model
        
        answer = service.generate_answer(
            query=query,
            retrieved_chunks=mock_chunks,
            chat_history=[]
        )
        
        assert "Mocked Answer" in answer
        mock_model.generate_content.assert_called_once()
        
        # Extract the prompt parameter passed
        called_prompt = mock_model.generate_content.call_args[0][0]
        
        # Verify strict prompt guidelines are attached
        assert "Answer ONLY using the provided context" in called_prompt
        assert "fastapi_manual.pdf" in called_prompt
        assert "PAGE: 12" in called_prompt
        assert "What is FastAPI?" in called_prompt
