from datetime import datetime, timezone
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class DocumentModel(BaseModel):
    document_id: str = Field(..., description="Unique document ID")
    title: str
    category: str = "general"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
