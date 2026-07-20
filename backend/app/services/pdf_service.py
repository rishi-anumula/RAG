import os
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class PDFProcessingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def extract_and_chunk(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from a PDF file page by page and chunks it.
        Returns a list of dictionaries, each containing:
            - text: str (the chunk content)
            - page: int (1-indexed page number)
            - chunk_index: int (within the document)
        """
        logger.info(f"Starting PDF processing for file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        chunks_data = []
        chunk_counter = 0

        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            logger.info(f"Successfully loaded PDF. Total pages: {num_pages}")
            
            for page_idx in range(num_pages):
                page_number = page_idx + 1
                try:
                    page = reader.pages[page_idx]
                    page_text = page.extract_text()
                    
                    if not page_text or not page_text.strip():
                        logger.info(f"Skipping empty or image-only page {page_number}")
                        continue
                    
                    # Clean up text slightly (remove null bytes, etc.)
                    clean_text = page_text.replace("\x00", "")
                    
                    # Split page text
                    page_chunks = self.splitter.split_text(clean_text)
                    logger.info(f"Split page {page_number} into {len(page_chunks)} chunks.")
                    
                    for chunk_txt in page_chunks:
                        if not chunk_txt.strip():
                            continue
                        chunks_data.append({
                            "text": chunk_txt.strip(),
                            "page": page_number,
                            "chunk_index": chunk_counter
                        })
                        chunk_counter += 1
                        
                except Exception as page_err:
                    logger.warning(f"Error extracting text from page {page_number}: {page_err}")
                    # Continue processing other pages even if one fails
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to read PDF file {file_path}: {e}", exc_info=True)
            raise ValueError(f"Corrupted or invalid PDF file: {e}")

        logger.info(f"PDF processing finished. Generated {len(chunks_data)} chunks in total.")
        return chunks_data

# Singleton instance
pdf_service = PDFProcessingService()
