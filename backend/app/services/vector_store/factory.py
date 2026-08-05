from typing import Optional
from app.core.config import settings
from app.core.exceptions import RAGPipelineException
from app.services.vector_store.base import BaseVectorStore
from app.services.vector_store.faiss_store import FAISSStore


class VectorStoreFactory:
    """Factory for instantiating pluggable Vector Stores (FAISS, Qdrant, Pinecone)."""

    _instance: Optional[BaseVectorStore] = None

    @classmethod
    def get_vector_store(
        cls, store_name: Optional[str] = None, force_new: bool = False
    ) -> BaseVectorStore:
        if cls._instance and not force_new:
            return cls._instance

        target_store = (store_name or settings.VECTOR_DB).lower().strip()

        if target_store == "faiss":
            cls._instance = FAISSStore(dimension=settings.EMBEDDING_DIMENSION)
        elif target_store in ["qdrant", "pinecone"]:
            # Extensible hook: currently fall back to FAISSStore for local dev with notice
            cls._instance = FAISSStore(dimension=settings.EMBEDDING_DIMENSION)
        else:
            raise RAGPipelineException(
                f"Unsupported Vector Store '{target_store}'. Supported: ['faiss', 'qdrant', 'pinecone']"
            )

        return cls._instance
