import pytest
from app.embeddings.embedder import embedding_service

def test_single_embedding():
    """
    Ensures that a single string generates a correct 384-dimension vector.
    """
    text = "Hello, RAG Search Workspace!"
    embedding = embedding_service.get_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(x, float) for x in embedding)

def test_batch_embeddings():
    """
    Ensures that multiple text strings produce multiple matching 384-dimension vectors.
    """
    texts = ["Segment A", "Segment B", "Segment C"]
    embeddings = embedding_service.get_embeddings(texts)
    
    assert isinstance(embeddings, list)
    assert len(embeddings) == len(texts)
    for embedding in embeddings:
        assert len(embedding) == 384
