from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class VectorDocument(BaseModel):
    """Container for vector document text, vector, and metadata."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None


class SearchResult(BaseModel):
    """Container for vector search match results."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = {}
    score: float  # Similarity score


class BaseVectorStore(ABC):
    """Abstract Base Class for Vector Stores (FAISS, Qdrant, Pinecone)."""

    @abstractmethod
    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        """Index documents into the vector store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform similarity search for query vector."""
        pass

    @abstractmethod
    async def delete(self, doc_ids: List[str]) -> bool:
        """Remove documents by ID."""
        pass

    @abstractmethod
    async def save(self, path: str) -> None:
        """Persist index to file or remote destination."""
        pass

    @abstractmethod
    async def load(self, path: str) -> None:
        """Load index from file or remote destination."""
        pass
