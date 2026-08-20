from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from ..database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)  # e.g. "PAY-EDK-xxx"
    order_id = Column(String, ForeignKey("orders.id"), index=True, nullable=False)
    user_id = Column(String, nullable=True, index=True)
    gateway = Column(String, nullable=False, default="cashfree")
    gateway_order_id = Column(String, nullable=True, index=True, unique=True)
    gateway_payment_id = Column(String, nullable=True, index=True, unique=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    status = Column(String, nullable=False, default="PENDING", index=True)  # SUCCESS, FAILED, PENDING, CANCELLED
    payment_method = Column(String, nullable=True)  # UPI, CARD, NETBANKING, WALLET
    raw_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class PaymentEvent(Base):
    """Audit log for all payment events (Orders, Sessions, Webhooks, Verifications)"""
    __tablename__ = "payment_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    # PAYMENT_ORDER_CREATED, PAYMENT_SESSION_CREATED, PAYMENT_INITIATED, PAYMENT_SUCCESS,
    # PAYMENT_FAILED, PAYMENT_CANCELLED, WEBHOOK_RECEIVED, PAYMENT_VERIFIED, ORDER_MARKED_PAID
    event_data = Column(Text, nullable=True)  # Sanitized JSON (no card/UPI PINs)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
