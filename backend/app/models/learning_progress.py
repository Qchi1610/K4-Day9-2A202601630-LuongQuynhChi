from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class LearningProgressModel(BaseModel):
    progress_id: str = Field(..., description="Unique progress record ID")
    user_id: str
    completed_topics: List[str] = Field(default_factory=list)
    quiz_scores: List[dict] = Field(default_factory=list)
    next_recommended_lessons: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
