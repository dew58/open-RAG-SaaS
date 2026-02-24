"""
Application configuration using Pydantic BaseSettings.

Architecture Decision:
- Pydantic v2 BaseSettings reads from environment variables and .env files
- Separate validator methods for computed/derived settings
- No hardcoded secrets anywhere — all from environment
- Environment-specific behavior via ENVIRONMENT field
"""

import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, model_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(64)  # Override in production!
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WORKERS: int = 4

    # ── Database ─────────────────────────────────────────────────────────────
    # Use asyncpg driver for async SQLAlchemy
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/rag_saas"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600  # Recycle connections every hour to prevent stale connections

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = secrets.token_urlsafe(64)  # Override in production!
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Provider Selection ────────────────────────────────────────────────────
    # LLM_PROVIDER: "gemini" (default)
    # EMBEDDING_PROVIDER: "gemini" (default) | "ollama" (requires local Ollama)
    LLM_PROVIDER: str = "gemini"
    EMBEDDING_PROVIDER: str = "gemini"

    # ── Gemini / Google AI (LLM + Embeddings) ─────────────────────────────────
    # Get your API key: https://aistudio.google.com/apikey
    GEMINI_API_KEY: str = ""                   # Required — set in .env
    GEMINI_MODEL: str = "models/gemma-3-12b-it"   # Gemma 3 12B (30 RPM free tier)
    GEMINI_MAX_TOKENS: int = 2048
    GEMINI_TEMPERATURE: float = 0.01            # Deterministic for RAG
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"  # DO NOT CHANGE

    # ── Ollama (optional, local embeddings) ──────────────────────────────────
    # Only used when EMBEDDING_PROVIDER=ollama
    # Run Ollama locally: https://ollama.com/download
    # Pull embedding model: ollama pull nomic-embed-text
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    # Each tenant gets an isolated collection: "client_{client_id}"
    # This provides logical separation without running multiple Chroma instances

    # ── File Storage ─────────────────────────────────────────────────────────
    UPLOAD_BASE_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "txt"]
    # Files are stored as: uploads/{client_id}/{uuid4}_{safe_filename}
    # This prevents path traversal AND handles duplicate names

    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_CHAT_REQUESTS: int = 20  # Stricter limit for expensive RAG queries
    RATE_LIMIT_CHAT_WINDOW_SECONDS: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" for production, "text" for development
    LOG_FILE: Optional[str] = "./logs/app.log"

    # ── RAG Pipeline ─────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 2000           # Larger chunks = fewer embedding API calls
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_TOP_K: int = 5         # Number of chunks to retrieve per query
    MAX_QUERY_LENGTH: int = 2000     # Prevent prompt injection via oversized inputs

    # ── API Rate Limits (Google AI Free Tier) ────────────────────────────────
    EMBEDDING_RPM: int = 100         # gemini-embedding-001 limit
    LLM_RPM: int = 30               # gemma-3-12b limit
    EMBEDDING_BATCH_SIZE: int = 10   # Chunks per embedding API call

    # ── Security ─────────────────────────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12  # Increase to 13-14 in production
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Ensure production deployments don't use default secrets."""
        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 chars in production")
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 chars in production")
        return self

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings instance.
    lru_cache ensures Settings() is called once — environment parsing is expensive.
    Call get_settings() everywhere instead of instantiating Settings() directly.
    """
    return Settings()


# Module-level convenience reference
settings = get_settings()
