from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class TicketCreateRequest(BaseModel):
    title: str
    description: str
    category: str = "technical_issue"
    priority: str = "medium"
    required_screenshots: List[str] = []


class TicketResponse(BaseModel):
    ticket_id: str
    session_id: str
    user_id: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    created_at: datetime
