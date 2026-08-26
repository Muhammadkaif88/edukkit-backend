import json
import logging
import time
from datetime import datetime, date, time as dtime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from ..database import get_db
from ..models.user import User
from ..models.course import Course
from ..models.lesson import Lesson
from ..models.product import Product
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.entitlement import CourseEntitlement
from ..middleware.auth_middleware import get_current_admin, get_current_staff_or_admin

logger = logging.getLogger("admin_routes")
router = APIRouter()


from datetime import datetime, timezone
def _serialize_admin_order(order: Order) -> dict:
    try:
        items_data = []
        if getattr(order, "items_json", None):
            try:
                items_data = json.loads(order.items_json)
            except Exception:
                items_data = []

        shipping_addr = None
        if getattr(order, "shipping_address_json", None):
            try:
                shipping_addr = json.loads(order.shipping_address_json)
            except Exception:
                shipping_addr = order.shipping_address_json

        return {
            "id": getattr(order, "id", ""),
            "user_id": getattr(order, "user_id", None),
            "customer_name": getattr(order, "customer_name", "Customer"),
            "customer_email": getattr(order, "customer_email", ""),
            "customer_phone": getattr(order, "customer_phone", ""),
            "items": items_data,
            "items_total": getattr(order, "items_total", 0.0),
            "delivery_fee": getattr(order, "delivery_fee", 0.0),
            "delivery_region": getattr(order, "delivery_region", "Digital/DIY"),
            "delivery_fee_rule": getattr(order, "delivery_fee_rule", "FREE_DELIVERY"),
            "discount_amount": getattr(order, "discount_amount", 0.0),
            "total_payable": getattr(order, "total_payable", 0.0),
            "currency": getattr(order, "currency", "INR"),
            "shipping_address": shipping_addr,
            "payment_status": getattr(order, "payment_status", "PAYMENT_PENDING"),
            "order_status": getattr(order, "order_status", "PENDING_PAYMENT"),
            "payment_method": getattr(order, "payment_method", "Cashfree Online"),
            "cashfree_order_id": getattr(order, "cashfree_order_id", None),
            "cashfree_payment_id": getattr(order, "cashfree_payment_id", None),
            "tracking_number": getattr(order, "tracking_number", None),
            "razorpay_order_id": getattr(order, "razorpay_order_id", None),
            "created_at": order.created_at.isoformat() if getattr(order, "created_at", None) else None,
            "updated_at": order.updated_at.isoformat() if getattr(order, "updated_at", None) else None,
        }
    except Exception as e:
        logger.error(f"Error serializing order: {e}")
        return {
            "id": getattr(order, "id", "unknown"),
            "user_id": getattr(order, "user_id", None),
            "customer_name": getattr(order, "customer_name", "Customer"),
            "customer_email": getattr(order, "customer_email", ""),
            "items": [],
            "items_total": 0.0,
            "delivery_fee": 0.0,
            "discount_amount": 0.0,
            "total_payable": getattr(order, "total_payable", 0.0),
            "currency": "INR",
            "payment_status": getattr(order, "payment_status", "PAYMENT_PENDING"),
            "order_status": getattr(order, "order_status", "PENDING_PAYMENT"),
            "created_at": None,
        }


# ==============================================================================
# 1. STATS & ANALYTICS
# ==============================================================================

@router.get("/stats")
def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    High-level dashboard KPIs and operational counters.
    """
    try:
        total_students = db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0
        total_teachers = db.query(func.count(User.id)).filter(User.role == "teacher").scalar() or 0
        total_admins = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
        
        total_courses = db.query(func.count(Course.id)).scalar() or 0
        published_courses = db.query(func.count(Course.id)).filter(Course.is_published == True).scalar() or 0
        total_lessons = db.query(func.count(Lesson.id)).scalar() or 0

        total_products = db.query(func.count(Product.id)).scalar() or 0
        low_stock_products = db.query(func.count(Product.id)).filter(Product.stock <= 5, Product.is_active == True).scalar() or 0

        total_orders = db.query(func.count(Order.id)).scalar() or 0
        paid_orders = db.query(func.count(Order.id)).filter(Order.payment_status == "PAYMENT_SUCCESS").scalar() or 0
        total_revenue = db.query(func.sum(Order.total_payable)).filter(Order.payment_status == "PAYMENT_SUCCESS").scalar() or 0.0

        today_orders = 0
        try:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_orders = db.query(func.count(Order.id)).filter(Order.created_at >= today_start).scalar() or 0
        except Exception as e:
            logger.warning(f"Error computing today_orders: {e}")

        pending_orders = 0
        try:
            pending_orders = db.query(func.count(Order.id)).filter(
                (Order.order_status.in_(["PENDING_PAYMENT", "PAID", "PROCESSING", "CONFIRMED"])) |
                (Order.payment_status == "PAYMENT_PENDING")
            ).scalar() or 0
        except Exception as e:
            logger.warning(f"Error computing pending_orders: {e}")

        recent_orders = []
        try:
            recent_orders_raw = db.query(Order).order_by(desc(Order.created_at)).limit(5).all()
            recent_orders = [_serialize_admin_order(o) for o in recent_orders_raw]
        except Exception as e:
            logger.error(f"Error fetching recent orders: {e}")

        active_entitlements = 0
        try:
            active_entitlements = db.query(func.count(CourseEntitlement.id)).filter(CourseEntitlement.status == "ACTIVE").scalar() or 0
        except Exception as e:
            logger.warning(f"Error computing active_entitlements: {e}")

        return {
            "users": {
                "total_students": total_students,
                "total_teachers": total_teachers,
                "total_admins": total_admins,
                "total_users": total_students + total_teachers + total_admins,
            },
            "courses": {
                "total_courses": total_courses,
                "published_courses": published_courses,
                "draft_courses": total_courses - published_courses,
                "total_lessons": total_lessons,
            },
            "store": {
                "total_products": total_products,
                "low_stock_count": low_stock_products,
            },
            "orders": {
                "total_orders": total_orders,
                "today_orders": today_orders,
                "paid_orders": paid_orders,
                "pending_orders": pending_orders,
                "total_revenue": round(float(total_revenue), 2),
                "recent_orders": recent_orders,
            },
            "entitlements": {
                "active_enrollments": active_entitlements,
            },
        }
    except Exception as e:
        logger.error(f"Critical error in get_admin_stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load admin telemetry: {str(e)}",
        )


# ==============================================================================
# 2. COURSE & CURRICULUM MANAGEMENT
# ==============================================================================

def _serialize_admin_course(course: Course, include_lessons: bool = False) -> dict:
    data = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "short_description": course.short_description,
        "thumbnail": course.thumbnail,
        "price": course.price,
        "original_price": course.original_price,
        "category": course.category,
        "level": course.level,
        "instructor": course.instructor,
        "bunny_collection_id": course.bunny_collection_id,
        "teacher_id": course.teacher_id,
        "is_published": course.is_published,
        "is_free": course.is_free,
        "lessons_count": len(course.lessons) if course.lessons is not None else 0,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }
    if include_lessons and course.lessons is not None:
        data["lessons"] = [
            {
                "id": l.id,
                "course_id": l.course_id,
                "title": l.title,
                "description": l.description,
                "video_stream_id": l.video_stream_id,
                "duration": l.duration,
                "order_index": l.order_index,
                "is_free_preview": l.is_free_preview,
                "notes_pdf": l.notes_pdf,
                "circuit_diagram": l.circuit_diagram,
            }
            for l in course.lessons
        ]
    return data


@router.get("/courses")
def get_admin_courses(
    category: Optional[str] = None,
    status_filter: Optional[str] = None,  # 'published' or 'draft'
    admin: User = Depends(get_current_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Lists all courses (published & draft) with full lesson metrics.
    """
    query = db.query(Course).options(joinedload(Course.lessons))
    if category:
        query = query.filter(Course.category.ilike(f"%{category}%"))
    if status_filter == "published":
        query = query.filter(Course.is_published == True)
    elif status_filter == "draft":
        query = query.filter(Course.is_published == False)

    courses = query.order_by(Course.id.asc()).all()
    return [_serialize_admin_course(c) for c in courses]


@router.get("/courses/{course_id}")
def get_admin_course_detail(
    course_id: int,
    admin: User = Depends(get_current_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Returns full details for a course, including all lessons and video IDs.
    """
    course = (
        db.query(Course)
        .options(joinedload(Course.lessons))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return _serialize_admin_course(course, include_lessons=True)


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def create_admin_course(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Creates a new course record.
    """
    course = Course(
        title=body.get("title", "").strip(),
        description=body.get("description"),
        short_description=body.get("short_description"),
        thumbnail=body.get("thumbnail"),
        price=float(body.get("price", 0.0)),
        original_price=float(body.get("original_price")) if body.get("original_price") else None,
        category=body.get("category"),
        level=body.get("level", "Beginner"),
        instructor=body.get("instructor", admin.name or "Edukkit Instructor"),
        bunny_collection_id=body.get("bunny_collection_id"),
        teacher_id=body.get("teacher_id") or admin.id,
        is_published=bool(body.get("is_published", False)),
        is_free=bool(body.get("is_free", False)),
    )
    if not course.title:
        raise HTTPException(status_code=400, detail="Course title is required.")

    db.add(course)
    db.commit()
    db.refresh(course)
    return _serialize_admin_course(course, include_lessons=True)


@router.put("/courses/{course_id}")
def update_admin_course(
    course_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Updates course metadata, pricing, and publish status.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if "title" in body:
        course.title = body["title"].strip()
    if "description" in body:
        course.description = body["description"]
    if "short_description" in body:
        course.short_description = body["short_description"]
    if "thumbnail" in body:
        course.thumbnail = body["thumbnail"]
    if "price" in body:
        course.price = float(body["price"])
    if "original_price" in body:
        course.original_price = float(body["original_price"]) if body["original_price"] is not None else None
    if "category" in body:
        course.category = body["category"]
    if "level" in body:
        course.level = body["level"]
    if "instructor" in body:
        course.instructor = body["instructor"]
    if "bunny_collection_id" in body:
        course.bunny_collection_id = body["bunny_collection_id"]
    if "is_published" in body:
        course.is_published = bool(body["is_published"])
    if "is_free" in body:
        course.is_free = bool(body["is_free"])

    db.commit()
    db.refresh(course)
    return _serialize_admin_course(course, include_lessons=True)


@router.delete("/courses/{course_id}")
def delete_admin_course(
    course_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Deletes a course and its associated lessons.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Delete attached lessons first
    db.query(Lesson).filter(Lesson.course_id == course_id).delete()
    db.delete(course)
    db.commit()
    return {"success": True, "message": f"Course {course_id} deleted successfully."}


# ==============================================================================
# 3. LESSON MANAGEMENT
# ==============================================================================

@router.post("/courses/{course_id}/lessons", status_code=status.HTTP_201_CREATED)
def create_admin_lesson(
    course_id: int,
    body: dict,
    admin: User = Depends(get_current_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Adds a new lesson to a course.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Determine order index if not provided
    existing_count = db.query(func.count(Lesson.id)).filter(Lesson.course_id == course_id).scalar() or 0
    order_index = int(body.get("order_index", existing_count + 1))

    lesson = Lesson(
        course_id=course_id,
        title=body.get("title", f"Lesson {order_index}").strip(),
        description=body.get("description"),
        video_stream_id=body.get("video_stream_id"),
        duration=int(body.get("duration", 0)) if body.get("duration") else None,
        notes_pdf=body.get("notes_pdf"),
        circuit_diagram=body.get("circuit_diagram"),
        order_index=order_index,
        is_free_preview=bool(body.get("is_free_preview", order_index <= 3)),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "description": lesson.description,
        "video_stream_id": lesson.video_stream_id,
        "duration": lesson.duration,
        "order_index": lesson.order_index,
        "is_free_preview": lesson.is_free_preview,
        "notes_pdf": lesson.notes_pdf,
        "circuit_diagram": lesson.circuit_diagram,
    }


@router.put("/lessons/{lesson_id}")
def update_admin_lesson(
    lesson_id: int,
    body: dict,
    admin: User = Depends(get_current_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Updates lesson metadata, video ID, notes, and free preview toggle.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if "title" in body:
        lesson.title = body["title"].strip()
    if "description" in body:
        lesson.description = body["description"]
    if "video_stream_id" in body:
        lesson.video_stream_id = body["video_stream_id"]
    if "duration" in body:
        lesson.duration = int(body["duration"]) if body["duration"] is not None else None
    if "notes_pdf" in body:
        lesson.notes_pdf = body["notes_pdf"]
    if "circuit_diagram" in body:
        lesson.circuit_diagram = body["circuit_diagram"]
    if "order_index" in body:
        lesson.order_index = int(body["order_index"])
    if "is_free_preview" in body:
        lesson.is_free_preview = bool(body["is_free_preview"])

    db.commit()
    db.refresh(lesson)
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "description": lesson.description,
        "video_stream_id": lesson.video_stream_id,
        "duration": lesson.duration,
        "order_index": lesson.order_index,
        "is_free_preview": lesson.is_free_preview,
        "notes_pdf": lesson.notes_pdf,
        "circuit_diagram": lesson.circuit_diagram,
    }


@router.delete("/lessons/{lesson_id}")
def delete_admin_lesson(
    lesson_id: int,
    admin: User = Depends(get_current_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Deletes a single lesson.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    course_id = lesson.course_id
    db.delete(lesson)
    db.commit()
    return {"success": True, "message": f"Lesson {lesson_id} deleted successfully.", "course_id": course_id}


@router.post("/courses/{course_id}/lessons/reorder")
def reorder_admin_lessons(
    course_id: int,
    body: Dict[str, List[int]],  # {"lesson_ids": [5, 2, 8, ...]}
    admin: User = Depends(get_current_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Reorders lessons in a course based on the provided list of lesson IDs.
    """
    lesson_ids = body.get("lesson_ids", [])
    if not lesson_ids:
        raise HTTPException(status_code=400, detail="lesson_ids array is required.")

    for index, l_id in enumerate(lesson_ids, start=1):
        db.query(Lesson).filter(Lesson.id == l_id, Lesson.course_id == course_id).update(
            {"order_index": index}
        )
    db.commit()
    return {"success": True, "message": "Lessons reordered successfully."}


# ==============================================================================
# 4. STORE & INVENTORY MANAGEMENT
# ==============================================================================

def _serialize_admin_product(product: Product) -> dict:
    images = []
    if product.images:
        try:
            images = json.loads(product.images)
        except Exception:
            images = [product.images] if product.images else []

    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "original_price": product.original_price,
        "stock": product.stock,
        "images": images,
        "category": product.category,
        "type": product.type,
        "is_active": product.is_active,
        "linked_course_id": product.linked_course_id,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


@router.get("/products")
def get_admin_products(
    product_type: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Lists all store products (active and inactive) with stock info.
    """
    query = db.query(Product)
    if product_type:
        query = query.filter(Product.type == product_type)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    products = query.order_by(Product.id.asc()).all()
    return [_serialize_admin_product(p) for p in products]


@router.get("/products/{product_id}")
def get_admin_product_detail(
    product_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Returns full product details.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize_admin_product(product)


@router.post("/products", status_code=status.HTTP_201_CREATED)
def create_admin_product(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Creates a new product (DIY kit or electronic component).
    """
    images_val = body.get("images", [])
    images_str = json.dumps(images_val) if isinstance(images_val, list) else images_val

    product = Product(
        name=body.get("name", "").strip(),
        description=body.get("description"),
        price=float(body.get("price", 0.0)),
        original_price=float(body.get("original_price")) if body.get("original_price") else None,
        stock=int(body.get("stock", 0)),
        images=images_str,
        category=body.get("category"),
        type=body.get("type", "diy_kit"),
        is_active=bool(body.get("is_active", True)),
        linked_course_id=int(body["linked_course_id"]) if body.get("linked_course_id") else None,
    )
    if not product.name:
        raise HTTPException(status_code=400, detail="Product name is required.")

    db.add(product)
    db.commit()
    db.refresh(product)
    return _serialize_admin_product(product)


@router.put("/products/{product_id}")
def update_admin_product(
    product_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Updates product pricing, inventory stock, images, or linked tutorial course.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if "name" in body:
        product.name = body["name"].strip()
    if "description" in body:
        product.description = body["description"]
    if "price" in body:
        product.price = float(body["price"])
    if "original_price" in body:
        product.original_price = float(body["original_price"]) if body["original_price"] is not None else None
    if "stock" in body:
        product.stock = int(body["stock"])
    if "images" in body:
        images_val = body["images"]
        product.images = json.dumps(images_val) if isinstance(images_val, list) else images_val
    if "category" in body:
        product.category = body["category"]
    if "type" in body:
        product.type = body["type"]
    if "is_active" in body:
        product.is_active = bool(body["is_active"])
    if "linked_course_id" in body:
        product.linked_course_id = int(body["linked_course_id"]) if body["linked_course_id"] is not None else None

    db.commit()
    db.refresh(product)
    return _serialize_admin_product(product)


@router.delete("/products/{product_id}")
def delete_admin_product(
    product_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Deletes or deactivates a product.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"success": True, "message": f"Product {product_id} deleted successfully."}


# ==============================================================================
# 5. ORDERS & FULFILLMENT MANAGEMENT
# ==============================================================================

@router.get("/orders")
def get_admin_orders(
    order_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Lists orders with search, status filters, and pagination.
    """
    query = db.query(Order)
    if order_status:
        query = query.filter(Order.order_status == order_status.upper())
    if payment_status:
        query = query.filter(Order.payment_status == payment_status.upper())
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (Order.id.ilike(term))
            | (Order.customer_name.ilike(term))
            | (Order.customer_email.ilike(term))
            | (Order.customer_phone.ilike(term))
            | (Order.cashfree_payment_id.ilike(term))
            | (Order.tracking_number.ilike(term))
        )

    total_count = query.count()
    orders = query.order_by(desc(Order.created_at)).offset(offset).limit(limit).all()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "orders": [_serialize_admin_order(o) for o in orders],
    }


@router.get("/orders/{order_id}")
def get_admin_order_detail(
    order_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Returns full order details for fulfillment processing.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        order = db.query(Order).filter(Order.cashfree_order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_admin_order(order)


# Status lifecycle ranking for fulfillment transition validation
STATUS_RANK = {
    "PENDING_PAYMENT": 0,
    "PAID": 1,
    "CONFIRMED": 2,
    "PROCESSING": 2,
    "PACKED": 3,
    "SHIPPED": 4,
    "DELIVERED": 5,
    "CANCELLED": 99,
}


@router.patch("/orders/{order_id}/status")
def update_admin_order_status(
    order_id: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Updates order lifecycle status with strict transition safety guardrails:
    - PAID -> CONFIRMED / PROCESSING -> PACKED -> SHIPPED -> DELIVERED
    - Unpaid orders (payment_status != PAYMENT_SUCCESS) cannot be confirmed or shipped
    - Invalid backward transitions are rejected
    - Automatically assigns tracking ID for physical orders if not present
    - Does NOT modify payment_status
    """
    raw_status = body.get("order_status")
    if not raw_status:
        raise HTTPException(status_code=400, detail="order_status is required.")

    new_status = raw_status.strip().upper()
    valid_statuses = [
        "PENDING_PAYMENT", "PAID", "CONFIRMED", "PROCESSING",
        "PACKED", "SHIPPED", "DELIVERED", "CANCELLED"
    ]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{raw_status}'. Allowed: {', '.join(valid_statuses)}",
        )

    # Normalize CONFIRMED alias to canonical PROCESSING
    if new_status == "CONFIRMED":
        new_status = "PROCESSING"

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        order = db.query(Order).filter(Order.cashfree_order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    current_status = order.order_status.upper()

    # Rule 1: Cannot fulfill an unpaid order
    if order.payment_status != "PAYMENT_SUCCESS":
        if new_status in ("PAID", "CONFIRMED", "PROCESSING", "PACKED", "SHIPPED", "DELIVERED"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot advance fulfillment status for unpaid order {order.id}. "
                    f"Current payment status is '{order.payment_status}'. "
                    f"Only verified paid orders can be fulfilled."
                ),
            )

    # Rule 2: Delivered orders are immutable
    if current_status == "DELIVERED" and new_status != "DELIVERED":
        raise HTTPException(
            status_code=400,
            detail=f"Order {order.id} is already DELIVERED and cannot be modified.",
        )

    # Rule 3: Cancelled orders are immutable
    if current_status == "CANCELLED" and new_status != "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail=f"Order {order.id} is CANCELLED and cannot be re-activated.",
        )

    # Rule 4: Reject invalid backward transitions
    current_rank = STATUS_RANK.get(current_status, 0)
    new_rank = STATUS_RANK.get(new_status, 0)

    if new_status != "CANCELLED" and new_rank < current_rank:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid backward transition from '{current_status}' to '{new_status}'.",
        )

    # Update lifecycle status
    order.order_status = new_status

    # Rule 5: Tracking number management
    custom_tracking = body.get("tracking_number")
    if custom_tracking and str(custom_tracking).strip():
        order.tracking_number = str(custom_tracking).strip()
    elif not order.tracking_number and new_status in ("CONFIRMED", "PROCESSING", "PACKED", "SHIPPED"):
        # Auto-generate tracking ID if missing
        order.tracking_number = f"EDK-TRK-{int(time.time() * 1000) % 10000000:07d}"

    # Sync fulfillment status on physical OrderItem records
    try:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        for item in items:
            if item.item_type in ("diy_kit", "electronics"):
                item.fulfillment_status = new_status
    except Exception as e:
        logger.warning(f"Failed to sync OrderItem fulfillment status for {order.id}: {e}")

    db.commit()
    db.refresh(order)

    return _serialize_admin_order(order)



# ==============================================================================
# 6. USERS & ENTITLEMENTS CONTROL
# ==============================================================================

@router.get("/users")
def get_admin_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Lists users with role and keyword filtering.
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%")) |
            (User.firebase_uid.ilike(f"%{search}%"))
        )

    total_count = query.count()
    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "users": [
            {
                "id": u.id,
                "firebase_uid": u.firebase_uid,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "role": u.role,
                "approval_status": u.approval_status,
                "is_verified": u.is_verified,
                "profile_image": u.profile_image,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.patch("/users/{user_id}/role")
def update_admin_user_role(
    user_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Elevates or changes a user's role ('student', 'teacher', 'admin', 'staff').
    """
    new_role = body.get("role")
    if new_role not in ("student", "teacher", "admin", "staff"):
        raise HTTPException(status_code=400, detail="Invalid role. Allowed: student, teacher, admin, staff")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    db.commit()
    db.refresh(user)
    return {
        "success": True,
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    }


@router.get("/users/{user_id}/entitlements")
def get_admin_user_entitlements(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Returns active and past course entitlements for a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    entitlements = db.query(CourseEntitlement).filter(
        (CourseEntitlement.user_id == user.firebase_uid) | (CourseEntitlement.user_id == str(user.id))
    ).all()

    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "course_id": e.course_id,
            "order_id": e.order_id,
            "status": e.status,
            "granted_at": e.granted_at.isoformat() if e.granted_at else None,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "revoked_at": e.revoked_at.isoformat() if e.revoked_at else None,
        }
        for e in entitlements
    ]


@router.post("/users/{user_id}/entitlements", status_code=status.HTTP_201_CREATED)
def grant_admin_course_entitlement(
    user_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Manually grants a user access to a course (e.g. offline student or customer support override).
    """
    course_id = body.get("course_id")
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    uid = user.firebase_uid or str(user.id)
    entitlement = db.query(CourseEntitlement).filter(
        CourseEntitlement.user_id == uid,
        CourseEntitlement.course_id == course_id,
    ).first()

    if entitlement:
        entitlement.status = "ACTIVE"
        entitlement.revoked_at = None
    else:
        entitlement = CourseEntitlement(
            user_id=uid,
            course_id=course_id,
            order_id=body.get("order_id") or "MANUAL_ADMIN_GRANT",
            status="ACTIVE",
        )
        db.add(entitlement)

    db.commit()
    db.refresh(entitlement)
    return {
        "success": True,
        "message": f"Access granted to course '{course.title}' for {user.email}.",
        "entitlement_id": entitlement.id,
        "status": entitlement.status,
    }


@router.delete("/users/{user_id}/entitlements/{course_id}")
def revoke_admin_course_entitlement(
    user_id: int,
    course_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Revokes a user's access to a course.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    uid = user.firebase_uid or str(user.id)
    entitlement = db.query(CourseEntitlement).filter(
        CourseEntitlement.user_id == uid,
        CourseEntitlement.course_id == course_id,
    ).first()

    if not entitlement:
        raise HTTPException(status_code=404, detail="Entitlement record not found")

    entitlement.status = "REVOKED"
    entitlement.revoked_at = func.now()
    db.commit()
    return {
        "success": True,
        "message": f"Course entitlement revoked for user {user.email}.",
        "status": "REVOKED",
    }
