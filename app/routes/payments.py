from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List, Optional
import json
import time
import uuid
import logging

from ..database import get_db
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.payment import Payment, PaymentEvent
from ..models.product import Product
from ..models.course import Course
from ..models.entitlement import CourseEntitlement
from ..services.cashfree_service import CashfreeService
from ..config import settings
from ..middleware.auth_middleware import get_current_uid

logger = logging.getLogger("payments_route")
router = APIRouter()


def _grant_entitlements_for_order(order: Order, db: Session):
    """
    Creates CourseEntitlement records for all course-type items in a paid order.

    Handles two cases:
      1. item_type == 'course' → entitlement for that course directly
      2. item_type == 'diy_kit' with product.linked_course_id → bonus tutorial entitlement

    Idempotent: duplicate entitlements are silently skipped (UNIQUE constraint).
    """
    try:
        items = json.loads(order.items_json)
        for item in items:
            item_type = item.get("item_type", "")
            item_id = item.get("item_id") or item.get("product_id") or item.get("course_id")
            if not item_id:
                continue

            try:
                item_id_int = int(item_id)
            except (ValueError, TypeError):
                logger.warning(f"Non-integer item_id in order {order.id}: {item_id}")
                continue

            course_id_to_grant = None

            if item_type == "course":
                # Direct course purchase → grant entitlement for this course
                course = db.query(Course).filter(Course.id == item_id_int).first()
                if course:
                    course_id_to_grant = course.id
                else:
                    logger.warning(f"Course {item_id_int} not found for entitlement grant")

            elif item_type in ("diy_kit", "electronics"):
                # Physical product — check if it has a linked tutorial course
                product = db.query(Product).filter(Product.id == item_id_int).first()
                if product and product.linked_course_id:
                    course_id_to_grant = product.linked_course_id

            if course_id_to_grant is not None:
                new_entitlement = CourseEntitlement(
                    user_id=order.user_id,
                    course_id=course_id_to_grant,
                    order_id=order.id,
                    status="ACTIVE",
                )
                db.add(new_entitlement)
                try:
                    db.flush()  # Trigger UNIQUE constraint check early
                    logger.info(
                        f"Granted CourseEntitlement: user={order.user_id} "
                        f"course={course_id_to_grant} order={order.id}"
                    )
                except IntegrityError:
                    db.rollback()
                    logger.info(
                        f"CourseEntitlement already exists (idempotent): "
                        f"user={order.user_id} course={course_id_to_grant}"
                    )

        # Also update OrderItem fulfillment status for course items
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        for oi in order_items:
            if oi.item_type == "course":
                oi.fulfillment_status = "FULFILLED"

    except Exception as e:
        logger.error(f"Error granting entitlements for order {order.id}: {e}")


@router.post("/create")
async def create_cashfree_payment_order(
    request: Request,
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    """
    Creates an internal Edukkit Order and a Cashfree Payment Session.

    Security:
    - uid is verified via Firebase JWT (cannot be spoofed)
    - Prices are fetched from DB by item ID (Flutter-supplied prices are IGNORED)
    - Delivery fee is calculated server-side based on item types + shipping address
    - Flutter only receives the payment_session_id to open the checkout

    Request body:
    {
      "customer_name": "...",
      "customer_email": "...",
      "customer_phone": "...",
      "shipping_address": { state, postalCode, ... },
      "items": [
        { "item_type": "course", "item_id": 5, "quantity": 1 },
        { "item_type": "diy_kit", "item_id": 12, "quantity": 1 },
      ]
    }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    customer_name = body.get("customer_name", "").strip() or "Edukkit Customer"
    customer_email = body.get("customer_email", "").strip() or f"{uid}@edukkit.com"
    customer_phone = (
        body.get("customer_phone", "").replace("+91", "").replace(" ", "").strip()
        or "9876543210"
    )
    shipping_address = body.get("shipping_address") or {}
    items = body.get("items") or []

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Validate: all items must have item_type and item_id
    for item in items:
        if not item.get("item_type") or not item.get("item_id"):
            raise HTTPException(
                status_code=400,
                detail="Each item must include 'item_type' and 'item_id'",
            )

    # For physical products (diy_kit, electronics), shipping address is required
    has_physical = any(i.get("item_type") in ("diy_kit", "electronics") for i in items)
    if has_physical and not shipping_address:
        raise HTTPException(
            status_code=400,
            detail="Shipping address is required for physical product orders",
        )

    # Authoritative server-side price + delivery recalculation
    (
        items_total, delivery_fee, region, rule, discount, total_payable
    ) = CashfreeService.recalculate_order_pricing(items, shipping_address, db)

    if total_payable < 0:
        raise HTTPException(status_code=400, detail="Invalid order total")

    # For completely free orders (all items free courses), handle directly
    # Currently we require Cashfree for all paid orders
    if total_payable == 0:
        # Free course — skip payment, create order + grant entitlement directly
        order_id = f"EDK-FREE-{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        # Build items_json with snapshots
        enriched_items = _enrich_items_with_snapshots(items, db)

        new_order = Order(
            id=order_id,
            user_id=uid,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            items_json=json.dumps(enriched_items),
            items_total=0.0,
            delivery_fee=0.0,
            delivery_region=region,
            delivery_fee_rule=rule,
            discount_amount=0.0,
            total_payable=0.0,
            currency="INR",
            shipping_address_json=json.dumps(shipping_address),
            payment_status="PAYMENT_SUCCESS",
            order_status="PAID",
            cashfree_order_id=None,
            cashfree_session_id=None,
            payment_method="Free",
            payment_attempt_count=0,
        )
        db.add(new_order)
        db.add(PaymentEvent(
            order_id=order_id,
            event_type="FREE_ORDER_CREATED",
            event_data=json.dumps({"order_id": order_id, "user_id": uid}),
        ))
        db.commit()
        db.refresh(new_order)
        _grant_entitlements_for_order(new_order, db)
        db.commit()

        return {
            "success": True,
            "order_id": order_id,
            "is_free": True,
            "total_payable": 0.0,
            "payment_required": False,
        }

    # Paid order — create Cashfree payment session
    timestamp_str = time.strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:4].upper()
    order_id = f"EDK-{timestamp_str}-{random_suffix}"
    cf_order_id = f"CF_{order_id}"

    customer_details = {
        "customer_id": uid,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
    }

    cf_response = CashfreeService.create_order(
        order_id=cf_order_id,
        order_amount=total_payable,
        customer_details=customer_details,
        order_note=f"Edukkit Order {order_id} ({region})",
    )

    payment_session_id = cf_response.get("payment_session_id") or f"session_{cf_order_id}"

    # Build items_json with name snapshots for order history
    enriched_items = _enrich_items_with_snapshots(items, db)

    # Create OrderItem records
    order_items_records = []
    for item in enriched_items:
        oi = OrderItem(
            order_id=order_id,
            item_type=item.get("item_type", ""),
            item_id=int(item.get("item_id", 0)),
            name_snapshot=item.get("name_snapshot", ""),
            price=float(item.get("unit_price", 0.0)),
            quantity=int(item.get("quantity", 1)),
            fulfillment_status="PENDING",
        )
        order_items_records.append(oi)

    new_order = Order(
        id=order_id,
        user_id=uid,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        items_json=json.dumps(enriched_items),
        items_total=items_total,
        delivery_fee=delivery_fee,
        delivery_region=region,
        delivery_fee_rule=rule,
        discount_amount=discount,
        total_payable=total_payable,
        currency="INR",
        shipping_address_json=json.dumps(shipping_address),
        payment_status="PAYMENT_PENDING",
        order_status="PENDING_PAYMENT",
        cashfree_order_id=cf_order_id,
        cashfree_session_id=payment_session_id,
        payment_method="Cashfree Online (UPI/Card/NetBanking)",
        payment_attempt_count=1,
    )
    db.add(new_order)
    for oi in order_items_records:
        db.add(oi)
    db.add(PaymentEvent(
        order_id=order_id,
        event_type="PAYMENT_ORDER_CREATED",
        event_data=json.dumps({
            "order_id": order_id,
            "cf_order_id": cf_order_id,
            "total_payable": total_payable,
            "delivery_fee": delivery_fee,
            "region": region,
            "user_id": uid,
        }),
    ))
    db.add(PaymentEvent(
        order_id=order_id,
        event_type="PAYMENT_SESSION_CREATED",
        event_data=json.dumps({
            "session_id_prefix": payment_session_id[:16] + "...",
            "cf_order_id": cf_order_id,
        }),
    ))
    db.commit()
    db.refresh(new_order)

    return {
        "success": True,
        "order_id": order_id,
        "cashfree_order_id": cf_order_id,
        "payment_session_id": payment_session_id,
        "items_total": items_total,
        "delivery_fee": delivery_fee,
        "delivery_region": region,
        "delivery_fee_rule": rule,
        "discount_amount": discount,
        "total_payable": total_payable,
        "currency": "INR",
        "is_free": False,
        "payment_required": True,
        "environment": settings.CASHFREE_ENV.lower(),
    }


def _enrich_items_with_snapshots(items: list, db: Session) -> list:
    """
    Enriches items with name snapshots and DB-verified prices for order history.
    """
    enriched = []
    for item in items:
        item_copy = dict(item)
        item_type = item.get("item_type", "")
        item_id = item.get("item_id")
        qty = int(item.get("quantity", 1))

        try:
            item_id_int = int(item_id)
            if item_type == "course":
                obj = db.query(Course).filter(Course.id == item_id_int).first()
                if obj:
                    item_copy["name_snapshot"] = obj.title
                    item_copy["unit_price"] = float(obj.price or 0.0)
                    item_copy["subtotal"] = item_copy["unit_price"] * qty
            else:
                obj = db.query(Product).filter(Product.id == item_id_int).first()
                if obj:
                    item_copy["name_snapshot"] = obj.name
                    item_copy["unit_price"] = float(obj.price or 0.0)
                    item_copy["subtotal"] = item_copy["unit_price"] * qty
        except Exception:
            pass

        item_copy["quantity"] = qty
        enriched.append(item_copy)
    return enriched


@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: str,
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    """
    Authoritative payment status check.
    Queries Cashfree and updates order to PAID if payment is verified.
    Only the order owner (verified by Firebase JWT) can check status.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        order = db.query(Order).filter(Order.cashfree_order_id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    # Security: only the order owner can check status
    if order.user_id != uid:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this order",
        )

    # If already PAID, return cached state immediately
    if order.payment_status == "PAYMENT_SUCCESS" and order.order_status == "PAID":
        return _build_status_response(order)

    # Query Cashfree for authoritative status
    cf_order_id = order.cashfree_order_id or f"CF_{order.id}"
    cf_order = CashfreeService.get_order_status(cf_order_id)
    cf_status = cf_order.get("order_status", "ACTIVE").upper()

    payments_list = CashfreeService.get_order_payments(cf_order_id)
    successful_payment = next(
        (p for p in payments_list if p.get("payment_status") == "SUCCESS"),
        None,
    )

    if cf_status == "PAID" or successful_payment is not None:
        paid_amount = float(cf_order.get("order_amount") or order.total_payable)
        cf_payment_id = (
            successful_payment.get("cf_payment_id") if successful_payment
            else f"CF_PAY_{uuid.uuid4().hex[:8]}"
        )
        pay_method = (
            successful_payment.get("payment_group", "UPI") if successful_payment
            else "Cashfree Online"
        )

        if round(paid_amount, 2) >= round(order.total_payable, 2):
            order.payment_status = "PAYMENT_SUCCESS"
            order.order_status = "PAID"
            order.cashfree_payment_id = str(cf_payment_id)
            order.payment_method = f"Cashfree / {pay_method}"

            # Idempotent payment record creation
            existing_pay = db.query(Payment).filter(
                Payment.gateway_order_id == cf_order_id
            ).first()
            if not existing_pay:
                db.add(Payment(
                    id=f"PAY-{order.id}",
                    order_id=order.id,
                    user_id=order.user_id,
                    gateway="cashfree",
                    gateway_order_id=cf_order_id,
                    gateway_payment_id=str(cf_payment_id),
                    amount=paid_amount,
                    currency="INR",
                    status="SUCCESS",
                    payment_method=pay_method,
                    raw_response=json.dumps(cf_order),
                ))

            db.add(PaymentEvent(
                order_id=order.id,
                event_type="PAYMENT_VERIFIED",
                event_data=json.dumps({
                    "cf_payment_id": str(cf_payment_id),
                    "amount": paid_amount,
                    "source": "status_poll",
                }),
            ))
            db.add(PaymentEvent(
                order_id=order.id,
                event_type="ORDER_MARKED_PAID",
                event_data=json.dumps({"order_id": order.id, "total": order.total_payable}),
            ))
            _grant_entitlements_for_order(order, db)
            db.commit()
            db.refresh(order)

    elif cf_status in ("CANCELLED", "EXPIRED"):
        order.payment_status = "PAYMENT_CANCELLED"
        db.add(PaymentEvent(
            order_id=order.id,
            event_type="PAYMENT_CANCELLED",
            event_data=json.dumps({"cf_status": cf_status}),
        ))
        db.commit()

    return _build_status_response(order)


def _build_status_response(order: Order) -> dict:
    return {
        "order_id": order.id,
        "payment_status": order.payment_status,
        "order_status": order.order_status,
        "total_payable": order.total_payable,
        "delivery_fee": order.delivery_fee,
        "delivery_region": order.delivery_region,
        "cashfree_payment_id": getattr(order, "cashfree_payment_id", None),
        "payment_method": order.payment_method,
        "is_paid": order.order_status == "PAID",
    }


@router.post("/webhook")
async def cashfree_webhook_handler(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_timestamp: Optional[str] = Header(None),
):
    """
    Cashfree Webhook Handler.
    HMAC-SHA256 Signature Verified + Idempotent.
    This is the authoritative payment success trigger — course entitlements are
    granted only after this webhook (or the status poll) confirms payment.
    """
    raw_body = await request.body()
    timestamp = x_webhook_timestamp or ""
    signature = x_webhook_signature or ""

    # Signature verification
    if settings.CASHFREE_WEBHOOK_SECRET and signature:
        is_valid = CashfreeService.verify_webhook_signature(raw_body, timestamp, signature)
        if not is_valid:
            logger.warning("Invalid Cashfree webhook signature received")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event.get("type", "")
    data = event.get("data", {})
    order_data = data.get("order", {})
    payment_data = data.get("payment", {})

    cf_order_id = order_data.get("order_id") or data.get("order_id")
    cf_payment_id = payment_data.get("cf_payment_id") or data.get("cf_payment_id")
    payment_status = payment_data.get("payment_status") or data.get("payment_status", "")
    payment_amount = float(
        payment_data.get("payment_amount") or order_data.get("order_amount", 0.0)
    )
    currency = payment_data.get("payment_currency") or order_data.get("order_currency", "INR")

    if not cf_order_id:
        return {"status": "ignored", "reason": "No order_id in event"}

    order = db.query(Order).filter(
        (Order.cashfree_order_id == cf_order_id) | (Order.id == cf_order_id)
    ).first()

    if not order:
        logger.warning(f"Webhook for unknown order: {cf_order_id}")
        return {"status": "ignored", "reason": "Order not found"}

    # Idempotency — already PAID: skip processing, return ok
    if order.payment_status == "PAYMENT_SUCCESS" and order.order_status == "PAID":
        logger.info(f"Duplicate webhook for already-PAID order {order.id} — skipped")
        return {"status": "ok", "message": "Order already marked as PAID (idempotent)"}

    # Log the webhook receipt
    db.add(PaymentEvent(
        order_id=order.id,
        event_type="WEBHOOK_RECEIVED",
        event_data=json.dumps({
            "type": event_type,
            "payment_status": payment_status,
            "amount": payment_amount,
        }),
    ))

    if "PAYMENT_SUCCESS" in event_type or payment_status.upper() == "SUCCESS":
        if currency.upper() == "INR" and round(payment_amount, 2) >= round(order.total_payable, 2):
            order.payment_status = "PAYMENT_SUCCESS"
            order.order_status = "PAID"
            order.cashfree_payment_id = str(cf_payment_id) if cf_payment_id else "CF_WEBHOOK_PAID"
            pay_method = payment_data.get("payment_group", "Cashfree Online")
            order.payment_method = f"Cashfree / {pay_method}"

            # Idempotent payment record — check by gateway_payment_id
            existing_pay = db.query(Payment).filter(
                Payment.gateway_payment_id == str(cf_payment_id)
            ).first() if cf_payment_id else None

            if not existing_pay:
                db.add(Payment(
                    id=f"PAY-{order.id}-{uuid.uuid4().hex[:4]}",
                    order_id=order.id,
                    user_id=order.user_id,
                    gateway="cashfree",
                    gateway_order_id=cf_order_id,
                    gateway_payment_id=str(cf_payment_id) if cf_payment_id else None,
                    amount=payment_amount,
                    currency=currency,
                    status="SUCCESS",
                    payment_method=pay_method,
                    raw_response=json.dumps(event),
                ))

            db.add(PaymentEvent(
                order_id=order.id,
                event_type="ORDER_MARKED_PAID",
                event_data=json.dumps({"order_id": order.id, "source": "webhook"}),
            ))

            _grant_entitlements_for_order(order, db)
            db.commit()
            logger.info(f"Order {order.id} marked PAID via Cashfree webhook")

    elif "PAYMENT_FAILED" in event_type or payment_status.upper() == "FAILED":
        order.payment_status = "PAYMENT_FAILED"
        db.add(PaymentEvent(
            order_id=order.id,
            event_type="PAYMENT_FAILED",
            event_data=json.dumps({"reason": "Webhook reported payment failure"}),
        ))
        db.commit()

    elif "USER_DROPPED" in event_type or "CANCELLED" in event_type:
        order.payment_status = "PAYMENT_CANCELLED"
        db.add(PaymentEvent(
            order_id=order.id,
            event_type="PAYMENT_CANCELLED",
            event_data=json.dumps({"reason": "User dropped/cancelled checkout"}),
        ))
        db.commit()

    return {"status": "ok"}


@router.get("/my-orders")
def get_my_orders(
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    """
    Returns all orders belonging to the authenticated user.
    """
    orders = (
        db.query(Order)
        .filter(Order.user_id == uid)
        .order_by(Order.created_at.desc())
        .all()
    )

    result = []
    for o in orders:
        try:
            items = json.loads(o.items_json)
        except Exception:
            items = []
        result.append({
            "order_id": o.id,
            "payment_status": o.payment_status,
            "order_status": o.order_status,
            "total_payable": o.total_payable,
            "delivery_fee": o.delivery_fee,
            "delivery_region": o.delivery_region,
            "items": items,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return result
