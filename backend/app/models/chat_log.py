from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatLogModel(BaseModel):
    log_id: str = Field(..., description="Unique chat log entry ID")
    request_id: str
    session_id: str
    user_id: str
    user_query: str
    agent_selected: List[str]
    response_content: str
    latency_ms: float
    tokens: int = 0
    cost: float = 0.0
    retrieved_documents: List[str] = Field(default_factory=list)
    tool_calls: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
