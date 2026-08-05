from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserModel(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    username: str
    email: str
    role: str = Field(default="sales_rep", description="User role: technician, sales_rep, store_manager, service_advisor")
    dealership_id: str = Field(default="dealership_001")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
