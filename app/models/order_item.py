from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class OrderItem(Base):
    """
    Individual line items within an order.

    item_type values:
      'course'      — digital course (grants CourseEntitlement on payment)
      'diy_kit'     — physical DIY kit (delivery FREE)
      'electronics' — physical electronics component (delivery charged ₹70/₹100)

    item_id references:
      courses.id    when item_type = 'course'
      products.id   when item_type = 'diy_kit' or 'electronics'

    Price snapshot fields capture the price at time of order.
    Later changes to product/course prices do NOT affect historical orders.
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    item_type = Column(String, nullable=False)              # 'course', 'diy_kit', 'electronics'
    item_id = Column(Integer, nullable=False)               # Course ID or Product ID
    name_snapshot = Column(String, nullable=True)           # Name at time of order (display)
    price = Column(Float, nullable=False, default=0.0)      # Unit price snapshot at order time
    quantity = Column(Integer, nullable=False, default=1)
    fulfillment_status = Column(String, nullable=True, default="PENDING")
    # PENDING, PAID, PROCESSING, PACKED, SHIPPED, DELIVERED, CANCELLED
    # Only relevant for physical items (diy_kit, electronics)
    # For course items: set to 'FULFILLED' after entitlement granted

    order = relationship("Order", back_populates="items")
