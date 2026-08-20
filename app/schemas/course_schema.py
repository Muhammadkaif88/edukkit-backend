from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CourseBase(BaseModel):
    title: str
    description: str
    thumbnail: Optional[str] = None
    price: float = 0.0
    category: str
    is_published: bool = False
    bunny_collection_id: Optional[str] = None

class CourseCreate(CourseBase):
    teacher_id: Optional[int] = None

class CourseResponse(CourseBase):
    id: int
    teacher_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
