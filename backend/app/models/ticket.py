from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TicketModel(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket ID")
    session_id: str
    user_id: str
    title: str
    description: str
    category: str = "technical_issue"
    priority: str = "medium"  # low, medium, high, critical
    required_screenshots: List[str] = Field(default_factory=list)
    status: str = "open"  # open, in_progress, resolved
    created_at: datetime = Field(default_factory=datetime.utcnow)
