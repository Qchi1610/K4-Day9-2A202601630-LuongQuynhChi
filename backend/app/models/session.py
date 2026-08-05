from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SessionModel(BaseModel):
    session_id: str = Field(..., description="Unique session UUID")
    user_id: str
    user_role: str = "sales_rep"
    current_workflow: Optional[str] = None
    retrieved_documents: List[str] = Field(default_factory=list)
    previous_questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
