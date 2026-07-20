import pytest
from app.services.pdf_service import PDFProcessingService

def test_chunking_logic():
    """
    Validates that the RecursiveCharacterTextSplitter splits documents correctly
    without exceeding the chunk size limitations.
    """
    service = PDFProcessingService(chunk_size=100, chunk_overlap=20)
    
    sample_text = (
        "Retrieval-Augmented Generation (RAG) is a technique for enhancing the accuracy "
        "and reliability of generative AI models by fetching facts from external search "
        "indexes or databases before compiling replies."
    )
    
    chunks = service.splitter.split_text(sample_text)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= 100
        # Check that it's not empty
        assert len(chunk.strip()) > 0
