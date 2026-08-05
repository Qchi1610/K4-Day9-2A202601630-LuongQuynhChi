import pytest
from app.core.config import settings


def test_settings_loaded():
    assert settings.APP_NAME is not None
    assert settings.LLM_PROVIDER in ["openai", "openrouter", "ollama"]
    assert settings.VECTOR_DB in ["faiss", "qdrant", "pinecone"]
