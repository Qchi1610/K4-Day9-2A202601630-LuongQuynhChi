from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or prompt message")
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")
    user_id: str = Field(default="user_001", description="User ID")
    user_role: str = Field(default="sales_rep", description="User role: technician, sales_rep, store_manager, service_advisor")


class AgentExecutionMetric(BaseModel):
    agent_name: str
    confidence: float
    citations: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_id: str
    session_id: str
    response: str
    agent_selected: List[str]
    citations: List[str] = Field(default_factory=list)
    latency_ms: float
    routing_scores: Dict[str, float] = Field(default_factory=dict)
