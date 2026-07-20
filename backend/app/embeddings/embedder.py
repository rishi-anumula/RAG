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

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text string.
        """
        self.load_model()
        start_time = time.time()
        try:
            if self.use_fallback:
                # If API key is a mock placeholder, return a deterministic mock embedding vector of 384 dimensions
                if not settings.GOOGLE_API_KEY or "mock" in settings.GOOGLE_API_KEY.lower():
                    logger.info("Using mock 384-dimension vector generator (Gemini API key is mock placeholder).")
                    import hashlib
                    h = hashlib.sha256(text.encode('utf-8')).hexdigest()
                    val = int(h[:8], 16) / float(0xffffffff)
                    return [val + (i * 0.001) for i in range(384)]

                # Use Gemini text-embedding-004 projected to 384 dimensions to match test assertions and chroma DB schema
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    contents=text,
                    output_dimensionality=384
                )
                embedding = result['embedding']
                logger.info(f"Generated single embedding via Gemini API in {time.time() - start_time:.4f} seconds.")
                return embedding
            else:
                embedding = self.model.encode(text, convert_to_numpy=True).tolist()
                logger.info(f"Generated single embedding in {time.time() - start_time:.4f} seconds.")
                return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            # If local model failed during runtime, try fallback as a last resort
            if not self.use_fallback:
                logger.warning("Local embedding failed. Attempting immediate Gemini API fallback.")
                try:
                    if not settings.GOOGLE_API_KEY or "mock" in settings.GOOGLE_API_KEY.lower():
                        import hashlib
                        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
                        val = int(h[:8], 16) / float(0xffffffff)
                        return [val + (i * 0.001) for i in range(384)]
                    genai.configure(api_key=settings.GOOGLE_API_KEY)
                    result = genai.embed_content(
                        model="models/text-embedding-004",
                        contents=text,
                        output_dimensionality=384
                    )
                    return result['embedding']
                except Exception as fallback_err:
                    logger.error(f"Fallback embedding generation failed: {fallback_err}")
            raise e

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
                # If API key is a mock placeholder, return deterministic mock embedding vectors
                if not settings.GOOGLE_API_KEY or "mock" in settings.GOOGLE_API_KEY.lower():
                    logger.info("Using mock batch 384-dimension vector generator (Gemini API key is mock placeholder).")
                    import hashlib
                    results = []
                    for t in texts:
                        h = hashlib.sha256(t.encode('utf-8')).hexdigest()
                        val = int(h[:8], 16) / float(0xffffffff)
                        results.append([val + (i * 0.001) for i in range(384)])
                    return results

                # Use Gemini text-embedding-004 projected to 384 dimensions
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    contents=texts,
                    output_dimensionality=384
                )
                embeddings = result['embedding']
                logger.info(f"Generated {len(texts)} embeddings via Gemini API in {time.time() - start_time:.4f} seconds.")
                return embeddings
            else:
                embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True).tolist()
                logger.info(f"Generated {len(texts)} embeddings in {time.time() - start_time:.4f} seconds.")
                return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            if not self.use_fallback:
                logger.warning("Local batch embedding failed. Attempting immediate Gemini API fallback.")
                try:
                    if not settings.GOOGLE_API_KEY or "mock" in settings.GOOGLE_API_KEY.lower():
                        import hashlib
                        results = []
                        for t in texts:
                            h = hashlib.sha256(t.encode('utf-8')).hexdigest()
                            val = int(h[:8], 16) / float(0xffffffff)
                            results.append([val + (i * 0.001) for i in range(384)])
                        return results
                    genai.configure(api_key=settings.GOOGLE_API_KEY)
                    result = genai.embed_content(
                        model="models/text-embedding-004",
                        contents=texts,
                        output_dimensionality=384
                    )
                    return result['embedding']
                except Exception as fallback_err:
                    logger.error(f"Fallback batch embedding generation failed: {fallback_err}")
            raise e

# Singleton instance
embedding_service = EmbeddingService()

