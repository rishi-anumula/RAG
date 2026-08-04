import time
import google.generativeai as genai
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.model_name = settings.GEMINI_MODEL_NAME
        self.initialized = False

    def init_client(self) -> None:
        """
        Configure the Google Gemini API client.
        """
        if not self.initialized:
            if not self.api_key:
                logger.error("GOOGLE_API_KEY is not configured. Gemini API will fail.")
                return
            try:
                genai.configure(api_key=self.api_key)
                self.initialized = True
                logger.info(f"Gemini client successfully initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)

    def generate_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, Any]] = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ) -> str:
        """
        Sends the retrieved context, chat history, and query to Google Gemini.
        Enforces constraints using system instructions.
        """
        self.init_client()
        if not self.initialized:
            return "Error: Gemini API is not configured. Please check your GOOGLE_API_KEY environment variable."

        # Compile Context
        context_str = ""
        if retrieved_chunks:
            for idx, item in enumerate(retrieved_chunks):
                meta = item.get("metadata", {})
                filename = meta.get("filename", "Unknown Document")
                page = meta.get("page", "Unknown Page")
                score = item.get("similarity", 0.0)
                chunk_text = item.get("chunk", "")
                
                context_str += f"\n--- SOURCE DOCUMENT: {filename} | PAGE: {page} | SIMILARITY SCORE: {score:.4f} ---\n"
                context_str += f"{chunk_text}\n"
        else:
            context_str = "No relevant context found in documents."

        # System Instructions
        system_instruction = (
            "You are an expert AI Assistant specializing in Document Analysis and Retrieval-Augmented Generation (RAG).\n"
            "Your task is to answer the USER QUERY directly, accurately, and thoroughly. Answer ONLY using the provided context.\n"
            "Guidelines:\n"
            "1. Answer specifically what the user asked. Do not repeat a fixed template or generic response.\n"
            "2. Base your response on the provided document context, citing the relevant source document name and page number.\n"
            "3. If the context covers part of the query, provide that information clearly.\n"
            "4. Keep your answer helpful, structured, and easy to read."
        )

        # Build prompt
        prompt = f"{system_instruction}\n\n"
        prompt += f"DOCUMENT CONTEXT:\n{context_str}\n\n"
        
        # Add chat history if present
        if chat_history and len(chat_history) > 0:
            prompt += "CONVERSATION HISTORY:\n"
            for msg in chat_history[-10:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                prompt += f"{role}: {msg.get('content')}\n"
            prompt += "\n"

        prompt += f"USER QUERY: {query}\n"
        prompt += "YOUR RESPONSE:"

        # Call Gemini with retry logic
        delay = 1.0
        last_exception = None
        
        # Determine valid model names dynamically, filtering out deprecated models
        available_models = []
        deprecated_models = {"gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.5-flash", "models/gemini-1.5-flash", "models/gemini-2.5-flash"}
        
        try:
            for m in genai.list_models():
                if "generateContent" in getattr(m, "supported_generation_methods", []):
                    name = m.name.replace("models/", "")
                    if name not in deprecated_models and m.name not in deprecated_models:
                        available_models.append(name)
                        available_models.append(m.name)
        except Exception as list_err:
            logger.warning(f"Could not list Gemini models dynamically: {list_err}")

        default_fallbacks = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-flash-latest",
            "gemini-pro-latest",
            self.model_name
        ]

        models_to_try = [m for m in (default_fallbacks + available_models) if m not in deprecated_models]
        seen = set()
        fallback_models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

        for m_name in fallback_models:
            try:
                start_time = time.time()
                logger.info(f"Sending prompt to Gemini model '{m_name}'. Query: {query[:50]}...")
                
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                    )
                )
                
                duration = time.time() - start_time
                if response and hasattr(response, "text") and response.text:
                    logger.info(f"Gemini model '{m_name}' responded in {duration:.2f} seconds.")
                    return response.text.strip()
            except Exception as e:
                last_exception = e
                logger.warning(f"Gemini API model '{m_name}' error: {e}")

        logger.warning(f"All Gemini API attempts failed ({last_exception}). Using direct RAG context synthesis fallback.")
        
        # Smart RAG Fallback: Synthesize answer directly from retrieved document context
        if retrieved_chunks:
            doc_name = retrieved_chunks[0].get("metadata", {}).get("filename", "your uploaded document")
            summary_parts = [
                f"Based on the extracted document context from **{doc_name}**:\n"
            ]
            for idx, item in enumerate(retrieved_chunks[:3]):
                page = item.get("metadata", {}).get("page", 1)
                chunk_txt = item.get("chunk", "").strip()
                summary_parts.append(f"**Section Citation (Page {page})**:\n> \"{chunk_txt}\"\n")
            return "\n".join(summary_parts)
        else:
            return "I couldn't find relevant information in the uploaded documents for your query."

# Singleton instance
gemini_service = GeminiService()
