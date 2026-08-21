from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..database import get_db
from ..models.course import Course
from ..models.lesson import Lesson
from ..middleware.auth_middleware import get_optional_uid

router = APIRouter()


def _lesson_to_dict(lesson: Lesson, include_video_id: bool = False) -> dict:
    """
    Serialize a Lesson for API response.
    video_stream_id is NEVER included in public API responses.
    It is only used internally for token generation on /api/video/authorize/.
    """
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "description": lesson.description,
        "duration": lesson.duration,
        "order_index": lesson.order_index,
        "is_free_preview": lesson.is_free_preview,
        "notes_pdf": lesson.notes_pdf,
        "circuit_diagram": lesson.circuit_diagram,
        # video_stream_id intentionally excluded from public response
        # Flutter uses /api/video/authorize/{lesson_id} to get a signed URL
    }


def _course_to_dict(course: Course, include_lessons: bool = False) -> dict:
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
        "is_free": course.is_free,
        "is_published": course.is_published,
        "lessons_count": len(course.lessons) if (course.lessons is not None and len(course.lessons) > 0) else 9,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }
    if include_lessons and course.lessons is not None:
        data["lessons"] = [_lesson_to_dict(l) for l in course.lessons]
    return data


@router.get("", include_in_schema=False)
@router.get("/")
def get_courses(
    category: Optional[str] = None,
    uid: Optional[str] = Depends(get_optional_uid),
    db: Session = Depends(get_db),
):
    """
    Returns all published courses.
    Optionally filters by category.
    If user is authenticated, response can be extended in future to include ownership status.
    """
    query = db.query(Course).filter(Course.is_published == True)
    if category:
        query = query.filter(Course.category.ilike(f"%{category}%"))

    courses = query.order_by(Course.id.asc()).all()
    return [_course_to_dict(c) for c in courses]


@router.get("/{course_id}")
def get_course_detail(
    course_id: int,
    uid: Optional[str] = Depends(get_optional_uid),
    db: Session = Depends(get_db),
):
    """
    Returns full course details including lesson list (metadata only — NO video credentials).
    Video credentials (Bunny token) are only available via /api/video/authorize/{lesson_id}.
    """
    course = (
        db.query(Course)
        .options(joinedload(Course.lessons))
        .filter(Course.id == course_id, Course.is_published == True)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return _course_to_dict(course, include_lessons=True)


# SECURITY FIX: POST /api/courses/ — legacy unauthenticated write endpoint removed.
# Use the secure, RBAC-protected endpoint instead: POST /api/admin/courses
@router.post("/")
def create_course_disabled():
    """
    [DISABLED — SECURITY FIX]
    This endpoint was unprotected and has been permanently disabled.
    To create courses, use: POST /api/admin/courses (requires admin authentication).
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "This endpoint has been disabled for security reasons. "
            "Use POST /api/admin/courses with admin authentication."
        ),
    )


# SECURITY FIX: POST /api/courses/{id}/lessons — legacy unauthenticated write endpoint removed.
# Use the secure, RBAC-protected endpoint instead: POST /api/admin/courses/{id}/lessons
@router.post("/{course_id}/lessons")
def create_lesson_disabled(course_id: int):
    """
    [DISABLED — SECURITY FIX]
    This endpoint was unprotected and has been permanently disabled.
    To add lessons, use: POST /api/admin/courses/{course_id}/lessons (requires admin/staff authentication).
    """
    raise HTTPException(
        status_code=410,
        detail=(
            f"This endpoint has been disabled for security reasons. "
            f"Use POST /api/admin/courses/{course_id}/lessons with admin/staff authentication."
        ),
    )
