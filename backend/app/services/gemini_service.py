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
            "You are an AI assistant.\n"
            "Answer ONLY using the provided context. Never use your own knowledge.\n"
            "If the answer does not exist in the provided context, respond EXACTLY with:\n"
            "\"I couldn't find this information in the uploaded documents.\"\n"
            "Do not try to make up, extrapolate, or use outside knowledge to answer.\n"
            "Include the source document name and page number whenever possible as inline or end-of-text citations."
        )

        # Build prompt
        prompt = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\n"
        prompt += f"CONTEXT:\n{context_str}\n\n"
        
        # Add chat history if present
        if chat_history and len(chat_history) > 0:
            prompt += "CONVERSATION HISTORY:\n"
            # Take only the last 10 messages to avoid context window explosion
            for msg in chat_history[-10:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                prompt += f"{role}: {msg.get('content')}\n"
            prompt += "\n"

        prompt += f"USER QUERY: {query}\n"
        prompt += "YOUR ANSWER (Strictly follow system instructions):"

        # Call Gemini with retry logic
        delay = 1.0
        last_exception = None
        
        models_to_try = [self.model_name, "gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-1.5-pro"]
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

        logger.error("All Gemini API attempts failed.", exc_info=True)
        return f"Error: Gemini API request failed. Details: {str(last_exception)}"

# Singleton instance
gemini_service = GeminiService()
