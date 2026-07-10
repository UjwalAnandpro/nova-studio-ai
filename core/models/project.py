from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProjectMetadata(BaseModel):
    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project Name")
    description: str = Field(default="", description="Project Description")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation ISO Timestamp")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last Update ISO Timestamp")
    duration: float = Field(default=0.0, description="Total video duration in seconds")
    status: str = Field(default="draft", description="Project status (draft, rendering, completed, error)")
    tags: List[str] = Field(default_factory=list, description="Tags associated with project")
    size_bytes: int = Field(default=0, description="Total storage size on disk")
