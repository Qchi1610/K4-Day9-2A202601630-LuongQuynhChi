from typing import Any, Dict, List
from pydantic import BaseModel
from app.services.vector_store.base import VectorDocument


class TextChunker:
    """Recursive character text splitter for chunking documents into vector items."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self, doc_id: str, title: str, content: str, metadata: Dict[str, Any] = None
    ) -> List[VectorDocument]:
        metadata = metadata or {}
        if not content:
            return []

        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            chunk_text = content[start:end]

            chunk_meta = {
                **metadata,
                "parent_doc_id": doc_id,
                "title": title,
                "chunk_index": chunk_idx,
            }

            chunks.append(
                VectorDocument(
                    doc_id=f"{doc_id}_chunk_{chunk_idx}",
                    content=chunk_text.strip(),
                    metadata=chunk_meta,
                )
            )

            if end == len(content):
                break
            start += self.chunk_size - self.chunk_overlap
            chunk_idx += 1

        return chunks
