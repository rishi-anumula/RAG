import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Supabase Connection settings
    SUPABASE_URL: str = Field(default="")
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    SECRET_KEY: str = Field(default="fallback_secret_key_for_development_only_change_in_prod")
    DATABASE_URL: str = Field(default="")
    UPLOAD_FOLDER: str = Field(default="/tmp/uploads" if os.getenv("VERCEL") else "./uploads")
    FRONTEND_URL: str = Field(default="")
    
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # RAG Settings
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    GEMINI_MODEL_NAME: str = Field(default="gemini-2.0-flash")
    USE_LOCAL_EMBEDDINGS: bool = Field(default=False)

    from pydantic import field_validator

    @field_validator(
        "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
        "GOOGLE_API_KEY", "SECRET_KEY", "DATABASE_URL",
        "UPLOAD_FOLDER", "HOST", "FRONTEND_URL",
        mode="before"
    )
    @classmethod
    def trim_spaces(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

# Global settings instance
settings = Settings()

# Ensure directories exist safely without throwing errors on read-only serverless environments
try:
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

try:
    log_dir = "/tmp/logs" if os.getenv("VERCEL") else "./logs"
    os.makedirs(log_dir, exist_ok=True)
except Exception:
    pass

