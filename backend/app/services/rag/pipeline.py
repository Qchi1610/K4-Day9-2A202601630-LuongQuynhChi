from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.models.document import DocumentModel
from app.services.database.repositories import document_repo
from app.services.rag.chunker import TextChunker
from app.services.rag.embedder import Embedder
from app.services.rag.loader import DocumentInput
from app.services.vector_store.base import SearchResult, VectorDocument
from app.services.vector_store.factory import VectorStoreFactory


class RAGSearchResult(BaseModel):
    answer: str
    citations: List[str]
    confidence: float
    retrieved_chunks: List[SearchResult]


class RAGPipeline:
    """End-to-end RAG Pipeline orchestrator."""

    def __init__(self):
        self.chunker = TextChunker()
        self.vector_store = VectorStoreFactory.get_vector_store()

    async def ingest_document(self, doc_input: DocumentInput) -> str:
        # Save to database
        db_doc = DocumentModel(
            document_id=doc_input.document_id,
            title=doc_input.title,
            category=doc_input.category,
            content=doc_input.content,
            metadata=doc_input.metadata,
        )
        await document_repo.insert(db_doc)

        # Chunk document
        chunks = self.chunker.chunk_document(
            doc_id=doc_input.document_id,
            title=doc_input.title,
            content=doc_input.content,
            metadata=doc_input.metadata,
        )

        if not chunks:
            return doc_input.document_id

        # Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = await Embedder.embed_texts(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        # Index in Vector Store
        await self.vector_store.add_documents(chunks)
        return doc_input.document_id

    async def retrieve(self, query: str, top_k: int = 4) -> List[SearchResult]:
        if not query.strip():
            return []

        embeddings = await Embedder.embed_texts([query])
        if not embeddings or not embeddings[0]:
            return []

        query_vec = embeddings[0]
        results = await self.vector_store.search(query_vector=query_vec, top_k=top_k)
        return results


rag_pipeline = RAGPipeline()
