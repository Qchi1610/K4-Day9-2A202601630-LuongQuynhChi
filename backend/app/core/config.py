import os
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Configuration
    APP_NAME: str = "Electric Motorcycle AI Onboarding Assistant"
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "development-secret-key-change-in-production-environment"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RATE_LIMIT_PER_MINUTE: int = 60
    PROMPT_INJECTION_PROTECTION: bool = True

    # Database (MongoDB)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "onboarding_db"

    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "openrouter", "ollama"] = "openai"
    MODEL_NAME: str = "gpt-4o"
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Vector Database & Embeddings
    VECTOR_DB: Literal["faiss", "qdrant", "pinecone"] = "faiss"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    FAISS_INDEX_PATH: str = "./data/faiss_index"

    # Confidence Thresholds
    TROUBLESHOOTING_CONFIDENCE_THRESHOLD: float = 0.70

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
