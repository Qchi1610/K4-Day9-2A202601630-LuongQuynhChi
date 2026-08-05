import uuid
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.rag import DocumentIngestRequest, DocumentIngestResponse
from app.services.database.repositories import document_repo
from app.services.rag.loader import DocumentInput
from app.services.rag.pipeline import rag_pipeline

router = APIRouter(prefix="/api/v1/documents", tags=["RAG Documents Ingestion"])


@router.post("/ingest", response_model=DocumentIngestResponse)
async def ingest_document(req: DocumentIngestRequest):
    """Ingest, chunk, embed, and index a document into RAG vector store."""
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    doc_input = DocumentInput(
        document_id=doc_id,
        title=req.title,
        content=req.content,
        category=req.category,
        metadata=req.metadata,
    )

    indexed_id = await rag_pipeline.ingest_document(doc_input)
    return DocumentIngestResponse(document_id=indexed_id, title=req.title, status="indexed")


@router.get("", response_model=List[dict])
async def list_documents():
    """List indexed documents."""
    docs = await document_repo.find_all(limit=50)
    return [doc.model_dump(mode="json") for doc in docs]
