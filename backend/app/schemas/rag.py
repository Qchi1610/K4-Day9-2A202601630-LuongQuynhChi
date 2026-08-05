from typing import Any, Dict, List
from pydantic import BaseModel


class DocumentIngestRequest(BaseModel):
    title: str
    content: str
    category: str = "general"
    metadata: Dict[str, Any] = {}


class DocumentIngestResponse(BaseModel):
    document_id: str
    title: str
    status: str = "indexed"
