import os
import gc
from typing import List, Dict, Any, Generator
from pypdf import PdfReader
from app.services.text_splitter import RecursiveCharacterTextSplitter
from app.core.logging_config import get_logger, get_memory_usage_mb

logger = get_logger(__name__)

class PDFProcessingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def extract_and_chunk_generator(self, file_path: str) -> Generator[Dict[str, Any], None, None]:
        """
        Streaming generator that parses a document page-by-page and yields chunk dictionaries immediately:
            - text: str (the chunk content)
            - page: int (1-indexed page number)
            - chunk_index: int (within the document)
        Avoids accumulating large PDF text structures in memory.
        """
        logger.info(f"[PDF GENERATOR START] File: {file_path} | Initial RAM: {get_memory_usage_mb():.2f} MB")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        chunk_counter = 0
        ext = os.path.splitext(file_path.lower())[1]

        # Support plain text, md, csv, json document files
        if ext in [".txt", ".md", ".csv", ".json", ".log"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()
                if full_text.strip():
                    text_chunks = self.splitter.split_text(full_text)
                    for idx, chunk_txt in enumerate(text_chunks):
                        if chunk_txt.strip():
                            yield {
                                "text": chunk_txt.strip(),
                                "page": 1,
                                "chunk_index": idx
                            }
                    logger.info(f"Text file generator finished. Memory: {get_memory_usage_mb():.2f} MB")
                    return
            except Exception as txt_err:
                logger.warning(f"Failed reading as plain text file: {txt_err}")

        # PDF page-by-page streaming extraction
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            logger.info(f"Successfully loaded PDF structure. Total pages: {num_pages} | RAM: {get_memory_usage_mb():.2f} MB")
            
            for page_idx in range(num_pages):
                page_number = page_idx + 1
                try:
                    page = reader.pages[page_idx]
                    page_text = page.extract_text()
                    
                    if not page_text or not page_text.strip():
                        logger.info(f"Skipping empty or image-only page {page_number}")
                        continue
                    
                    clean_text = page_text.replace("\x00", "")
                    page_chunks = self.splitter.split_text(clean_text)
                    
                    for chunk_txt in page_chunks:
                        if not chunk_txt.strip():
                            continue
                        yield {
                            "text": chunk_txt.strip(),
                            "page": page_number,
                            "chunk_index": chunk_counter
                        }
                        chunk_counter += 1
                    
                    del page, page_text, clean_text, page_chunks
                    
                except Exception as page_err:
                    logger.warning(f"Error extracting text from page {page_number}: {page_err}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to read PDF file {file_path}: {e}", exc_info=True)
            raise ValueError(f"Corrupted or invalid PDF file: {e}")
        finally:
            gc.collect()

        logger.info(f"[PDF GENERATOR END] Finished. Generated {chunk_counter} chunks | RAM: {get_memory_usage_mb():.2f} MB")

    def extract_and_chunk(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Backwards-compatible wrapper returning a list of all extracted chunk dictionaries.
        """
        return list(self.extract_and_chunk_generator(file_path))

# Singleton instance
pdf_service = PDFProcessingService()

