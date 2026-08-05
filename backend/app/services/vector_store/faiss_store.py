try:
    import faiss
    HAS_FAISS = True
except ImportError:
    faiss = None
    HAS_FAISS = False

import numpy as np

from app.core.config import settings
from app.core.exceptions import RAGPipelineException
from app.services.vector_store.base import BaseVectorStore, SearchResult, VectorDocument


class FAISSStore(BaseVectorStore):
    """FAISS-based Vector Database implementation with NumPy fallback."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(self.dimension) if HAS_FAISS else None
        self.documents: List[VectorDocument] = []
        self.doc_id_map: Dict[int, str] = {}  # Index position -> doc_id
        self.matrix: Optional[np.ndarray] = None

    def _normalize(self, vector: List[float]) -> np.ndarray:
        arr = np.array([vector], dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        if not documents:
            return []

        added_ids = []
        vectors_to_add = []

        for doc in documents:
            if not doc.embedding:
                raise RAGPipelineException(f"Document {doc.doc_id} missing embedding vector.")

            if len(doc.embedding) != self.dimension:
                # Handle dimension mismatch if needed or truncate/pad
                arr = np.array(doc.embedding[: self.dimension], dtype=np.float32)
                if len(arr) < self.dimension:
                    arr = np.pad(arr, (0, self.dimension - len(arr)))
            else:
                arr = np.array(doc.embedding, dtype=np.float32)

            vectors_to_add.append(arr)
            pos = len(self.documents)
            self.documents.append(doc)
            self.doc_id_map[pos] = doc.doc_id
            added_ids.append(doc.doc_id)

        if vectors_to_add:
            matrix = np.vstack(vectors_to_add)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
            if HAS_FAISS and self.index is not None:
                self.index.add(matrix)
            
            if self.matrix is None:
                self.matrix = matrix
            else:
                self.matrix = np.vstack([self.matrix, matrix])

        return added_ids

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        if not self.documents or not query_vector:
            return []

        q_norm = self._normalize(query_vector)

        if HAS_FAISS and self.index is not None and self.index.ntotal > 0:
            actual_k = min(top_k, self.index.ntotal)
            scores, indices = self.index.search(q_norm, actual_k)
            scores_list = scores[0]
            indices_list = indices[0]
        else:
            if self.matrix is None or len(self.matrix) == 0:
                return []
            sims = np.dot(self.matrix, q_norm.T).flatten()
            actual_k = min(top_k, len(sims))
            indices_list = np.argsort(-sims)[:actual_k]
            scores_list = sims[indices_list]

        results = []
        for score, idx in zip(scores_list, indices_list):
            if idx == -1 or idx >= len(self.documents):
                continue

            doc = self.documents[idx]
            
            if filter_metadata:
                match = all(doc.metadata.get(k) == v for k, v in filter_metadata.items())
                if not match:
                    continue

            results.append(
                SearchResult(
                    doc_id=doc.doc_id,
                    content=doc.content,
                    metadata=doc.metadata,
                    score=float(score),
                )
            )

        return results

    async def delete(self, doc_ids: List[str]) -> bool:
        # FAISS IndexFlatIP does not support in-place deletion easily.
        # We filter documents list and rebuild the index.
        to_delete_set = set(doc_ids)
        remaining_docs = [d for d in self.documents if d.doc_id not in to_delete_set]
        
        self.index.reset()
        self.documents = []
        self.doc_id_map = {}

        if remaining_docs:
            await self.add_documents(remaining_docs)
        return True

    async def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        index_file = f"{path}.index"
        data_file = f"{path}.pkl"

        faiss.write_index(self.index, index_file)
        with open(data_file, "wb") as f:
            pickle.dump({"documents": self.documents, "doc_id_map": self.doc_id_map}, f)

    async def load(self, path: str) -> None:
        index_file = f"{path}.index"
        data_file = f"{path}.pkl"

        if not (os.path.exists(index_file) and os.path.exists(data_file)):
            return  # Empty/New vector store

        self.index = faiss.read_index(index_file)
        with open(data_file, "rb") as f:
            payload = pickle.load(f)
            self.documents = payload.get("documents", [])
            self.doc_id_map = payload.get("doc_id_map", {})
