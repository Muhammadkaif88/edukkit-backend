from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    short_description = Column(String, nullable=True)    # Brief marketing description
    thumbnail = Column(String, nullable=True)             # URL to thumbnail image
    price = Column(Float, default=0.0, nullable=False)   # Current selling price (AUTHORITATIVE)
    original_price = Column(Float, nullable=True)         # Strike-through price for display
    category = Column(String, index=True, nullable=True)
    level = Column(String, nullable=True, default="Beginner")  # Beginner, Intermediate, Advanced
    instructor = Column(String, nullable=True)
    bunny_collection_id = Column(String, nullable=True)   # Bunny Stream collection ID
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_published = Column(Boolean, default=False)         # Only published courses served to Flutter
    is_free = Column(Boolean, default=False)              # True = no purchase required

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    teacher = relationship("User")
    lessons = relationship("Lesson", back_populates="course", order_by="Lesson.order_index")
