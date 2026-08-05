import json
from typing import List, Optional, Type
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.services.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Ollama Local LLM Provider Implementation using Async HTTPX."""

    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.MODEL_NAME

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

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
            except Exception as e:
                raise LLMProviderException("ollama", f"HTTP error calling Ollama at {self.base_url}: {e}")

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
                "ollama", f"Failed to parse structured response: {e}. Raw text: {raw_text}"
            )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        embeddings = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for text in texts:
                try:
                    payload = {"model": settings.EMBEDDING_MODEL, "prompt": text}
                    response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    embeddings.append(data.get("embedding", []))
                except Exception as e:
                    raise LLMProviderException("ollama", f"Embedding error for text '{text[:20]}...': {e}")
        return embeddings
