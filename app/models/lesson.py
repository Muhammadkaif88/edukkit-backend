from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    video_stream_id = Column(String, nullable=True)   # Bunny Stream video ID
    duration = Column(Integer, nullable=True)          # Duration in seconds
    notes_pdf = Column(String, nullable=True)          # URL or path to notes PDF
    circuit_diagram = Column(String, nullable=True)    # URL or path to circuit diagram
    order_index = Column(Integer, default=0)
    is_free_preview = Column(Boolean, default=False)   # True = accessible without purchase

    course = relationship("Course", back_populates="lessons")
