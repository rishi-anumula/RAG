import time
import os
from typing import List
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

import google.generativeai as genai

class EmbeddingService:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.model = None
        self.use_fallback = not settings.USE_LOCAL_EMBEDDINGS
        
        # Configure Gemini API if using fallback
        if self.use_fallback:
            logger.info("Configuring Gemini API key for embedding cloud service.")
            genai.configure(api_key=settings.GOOGLE_API_KEY)

    @property
    def is_mock_key(self) -> bool:
        key = settings.GOOGLE_API_KEY
        if not key:
            return True
        key_str = str(key).strip().strip('"').strip("'")
        return (
            "mock" in key_str.lower()
            or "placeholder" in key_str.lower()
            or key_str == "AIzaSyAjZVQLXaUgEIszIOUD3ws_qaYKkfaswek"
            or len(key_str) < 10
        )

    def load_model(self) -> None:
        """
        Lazy load the SentenceTransformer model if fallback is not active.
        """
        if self.use_fallback:
            logger.info("Using Google Gemini text-embedding-004 API as the active embedding provider.")
            return

        if self.model is None:
            logger.info(f"Initializing SentenceTransformer model: {self.model_name}")
            start_time = time.time()
            try:
                # Lazy-import sentence_transformers here to avoid loading heavy torch dlls if not needed
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded embedding model in {time.time() - start_time:.2f} seconds.")
            except Exception as e:
                logger.error(f"Failed to initialize local embedding model: {e}. Switching to Google Gemini cloud fallback.")
                self.use_fallback = True
                genai.configure(api_key=settings.GOOGLE_API_KEY)

    def _mock_vector(self, text: str) -> List[float]:
        import hashlib
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        val = int(h[:8], 16) / float(0xffffffff)
        return [val + (i * 0.001) for i in range(384)]

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text string.
        """
        self.load_model()
        start_time = time.time()
        try:
            if self.use_fallback:
                if self.is_mock_key:
                    logger.info("Using mock 384-dimension vector generator (Gemini API key is mock placeholder).")
                    return self._mock_vector(text)

                try:
                    result = genai.embed_content(
                        model="models/text-embedding-004",
                        content=text,
                        output_dimensionality=384
                    )
                    embedding = result['embedding']
                    logger.info(f"Generated single embedding via Gemini API in {time.time() - start_time:.4f} seconds.")
                    return embedding
                except Exception as api_err:
                    logger.warning(f"Gemini API embed_content failed ({api_err}). Falling back to mock 384-dimension vector generator.")
                    return self._mock_vector(text)
            else:
                embedding = self.model.encode(text, convert_to_numpy=True).tolist()
                logger.info(f"Generated single embedding in {time.time() - start_time:.4f} seconds.")
                return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return self._mock_vector(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate batch embedding vectors for a list of text strings.
        """
        if not texts:
            return []
        self.load_model()
        start_time = time.time()
        try:
            if self.use_fallback:
                if self.is_mock_key:
                    logger.info("Using mock batch 384-dimension vector generator (Gemini API key is mock placeholder).")
                    return [self._mock_vector(t) for t in texts]

                try:
                    result = genai.embed_content(
                        model="models/text-embedding-004",
                        content=texts,
                        output_dimensionality=384
                    )
                    embeddings = result['embedding']
                    logger.info(f"Generated {len(texts)} embeddings via Gemini API in {time.time() - start_time:.4f} seconds.")
                    return embeddings
                except Exception as api_err:
                    logger.warning(f"Gemini API batch embed_content failed ({api_err}). Falling back to mock 384-dimension vector generator.")
                    return [self._mock_vector(t) for t in texts]
            else:
                embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True).tolist()
                logger.info(f"Generated {len(texts)} embeddings in {time.time() - start_time:.4f} seconds.")
                return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            return [self._mock_vector(t) for t in texts]

# Singleton instance
embedding_service = EmbeddingService()

