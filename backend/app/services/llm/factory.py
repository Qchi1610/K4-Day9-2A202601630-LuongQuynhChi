from typing import Optional
from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.services.llm.base import BaseLLMProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.openrouter_provider import OpenRouterProvider
from app.services.llm.ollama_provider import OllamaProvider


class LLMFactory:
    """Factory for creating LLM Provider instances dynamically based on configuration."""

    _instance: Optional[BaseLLMProvider] = None

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None, force_new: bool = False) -> BaseLLMProvider:
        if cls._instance and not force_new:
            return cls._instance

        target_provider = (provider_name or settings.LLM_PROVIDER).lower().strip()

        if target_provider == "openai":
            cls._instance = OpenAIProvider()
        elif target_provider == "openrouter":
            cls._instance = OpenRouterProvider()
        elif target_provider == "ollama":
            cls._instance = OllamaProvider()
        else:
            raise LLMProviderException(
                target_provider, f"Unsupported LLM provider '{target_provider}'. Supported: ['openai', 'openrouter', 'ollama']"
            )

        return cls._instance
