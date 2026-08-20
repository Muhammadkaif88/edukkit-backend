from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class CourseEntitlement(Base):
    __tablename__ = "course_entitlements"

    # Prevent duplicate entitlements for same user+course combination
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_course_entitlement"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)         # Firebase UID string
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=True)  # Nullable for admin grants

    # Entitlement lifecycle status
    # ACTIVE   — user has full access to course
    # REVOKED  — access manually revoked by admin (e.g., chargeback)
    # EXPIRED  — access period ended (for time-limited courses)
    status = Column(String, nullable=False, default="ACTIVE", index=True)

    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)   # NULL = lifetime access
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    course = relationship("Course")
    order = relationship("Order")
