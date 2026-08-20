from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from ..database import Base


class Product(Base):
    """
    Products sold in the Edukkit store.

    type = 'diy_kit'     — DIY Kit (physical, delivery FREE)
    type = 'electronics' — Electronics component (physical, delivery charged: ₹70/₹100)

    If a DIY Kit has a linked_course_id, purchasing the kit also grants a
    CourseEntitlement for the linked tutorial course.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, default=0.0, nullable=False)      # AUTHORITATIVE selling price
    original_price = Column(Float, nullable=True)            # Strike-through price for display
    stock = Column(Integer, default=0)
    images = Column(String, nullable=True)                   # JSON array of image URLs as string
    category = Column(String, index=True, nullable=True)
    type = Column(String, nullable=False, default="diy_kit") # 'diy_kit' or 'electronics'
    is_active = Column(Boolean, default=True)                # False = hidden from catalog
    linked_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
