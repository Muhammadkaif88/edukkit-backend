from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)   # e.g. "EDK-20260817-ABCD"
    user_id = Column(String, index=True, nullable=True)  # Firebase UID string
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)

    # Cart / Items JSON (list of {item_type, item_id, name_snapshot, unit_price, quantity})
    items_json = Column(Text, nullable=False)

    # Price & Delivery breakdown
    items_total = Column(Float, nullable=False, default=0.0)
    delivery_fee = Column(Float, nullable=False, default=0.0)
    delivery_region = Column(String, nullable=False, default="Digital/DIY")
    delivery_fee_rule = Column(String, nullable=False, default="FREE_DELIVERY")
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_payable = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")

    # Shipping Address JSON
    shipping_address_json = Column(Text, nullable=True)

    # Order lifecycle
    payment_status = Column(String, nullable=False, default="PAYMENT_PENDING", index=True)
    # PAYMENT_PENDING, PAYMENT_PROCESSING, PAYMENT_SUCCESS,
    # PAYMENT_FAILED, PAYMENT_CANCELLED, PAYMENT_EXPIRED

    order_status = Column(String, nullable=False, default="PENDING_PAYMENT", index=True)
    # PENDING_PAYMENT, PAID, PROCESSING, PACKED, SHIPPED, DELIVERED, CANCELLED

    # Cashfree Gateway fields
    cashfree_order_id = Column(String, unique=True, index=True, nullable=True)
    cashfree_session_id = Column(String, nullable=True)
    cashfree_payment_id = Column(String, nullable=True)

    payment_method = Column(String, nullable=True, default="Cashfree Online")
    payment_attempt_count = Column(Integer, default=1)

    # Razorpay fields (used for Razorpay payment lifecycle)
    razorpay_order_id = Column(String, index=True, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    razorpay_signature = Column(String, nullable=True)


    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    items = relationship("OrderItem", back_populates="order")
