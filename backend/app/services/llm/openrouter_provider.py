import json
from typing import List, Optional, Type
from pydantic import BaseModel
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.services.llm.base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter LLM Provider Implementation (using OpenAI client with custom base_url)."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise LLMProviderException("openrouter", "OPENROUTER_API_KEY is not configured.")
        self.model_name = model_name or settings.MODEL_NAME
        self.embedding_model = settings.EMBEDDING_MODEL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMProviderException("openrouter", str(e))

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> BaseModel:
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_system = (
            (system_prompt or "") + 
            f"\n\nYou MUST return raw valid JSON matching this schema exactly:\n{schema_json}"
        )

        raw_text = await self.generate(
            prompt=prompt,
            system_prompt=augmented_system,
            temperature=temperature,
            max_tokens=2000,
        )

        try:
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            return response_model.model_validate(parsed)
        except Exception as e:
            raise LLMProviderException(
                "openrouter", f"Failed to parse structured response: {e}. Raw text: {raw_text}"
            )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Fallback to OpenAI embed or default embeddings if OpenRouter embeddings call fails
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            raise LLMProviderException("openrouter", f"Embedding failed: {e}")
