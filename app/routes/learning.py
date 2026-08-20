from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..database import get_db
from ..models.entitlement import CourseEntitlement
from ..models.course import Course
from ..models.order import Order
from ..middleware.auth_middleware import get_current_uid

router = APIRouter()


@router.get("/")
def get_my_learning(
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    """
    Returns all courses the authenticated user is actively entitled to.

    Requires Firebase JWT in Authorization header.
    uid extracted from verified JWT — cannot be spoofed.

    Returns: list of course objects with entitlement metadata.
    """
    entitlements = db.query(CourseEntitlement).filter(
        CourseEntitlement.user_id == uid,
        CourseEntitlement.status == "ACTIVE",
    ).all()

    if not entitlements:
        return []

    course_ids = [e.course_id for e in entitlements]
    courses = db.query(Course).filter(Course.id.in_(course_ids)).all()

    # Map entitlements by course_id for quick lookup
    entitlement_map = {e.course_id: e for e in entitlements}

    result = []
    for c in courses:
        ent = entitlement_map.get(c.id)
        result.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "short_description": c.short_description,
            "thumbnail": c.thumbnail,
            "category": c.category,
            "level": c.level,
            "instructor": c.instructor,
            "price": c.price,
            "is_free": c.is_free,
            "entitlement": {
                "status": ent.status if ent else "ACTIVE",
                "granted_at": ent.granted_at.isoformat() if ent and ent.granted_at else None,
                "expires_at": ent.expires_at.isoformat() if ent and ent.expires_at else None,
                "order_id": ent.order_id if ent else None,
            },
        })

    return result


@router.get("/check/{course_id}")
def check_course_access(
    course_id: int,
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    """
    Returns the authenticated user's access status for a specific course.
    Used by CourseDetailScreen to determine if user can access lessons.

    Returns:
      is_free: bool
      is_owned: bool
      entitlement_status: 'ACTIVE' | 'REVOKED' | 'EXPIRED' | 'NOT_PURCHASED'
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.is_free:
        return {
            "course_id": course_id,
            "is_free": True,
            "is_owned": True,
            "entitlement_status": "FREE",
            "price": 0.0,
        }

    entitlement = db.query(CourseEntitlement).filter(
        CourseEntitlement.user_id == uid,
        CourseEntitlement.course_id == course_id,
    ).first()

    if not entitlement:
        return {
            "course_id": course_id,
            "is_free": False,
            "is_owned": False,
            "entitlement_status": "NOT_PURCHASED",
            "price": course.price,
        }

    return {
        "course_id": course_id,
        "is_free": False,
        "is_owned": entitlement.status == "ACTIVE",
        "entitlement_status": entitlement.status,
        "granted_at": entitlement.granted_at.isoformat() if entitlement.granted_at else None,
        "expires_at": entitlement.expires_at.isoformat() if entitlement.expires_at else None,
        "price": course.price,
    }
