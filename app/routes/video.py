from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models.lesson import Lesson
from ..models.entitlement import CourseEntitlement
from ..services.video_service import VideoService
from ..middleware.auth_middleware import get_current_uid, get_optional_uid

router = APIRouter()


@router.get("/authorize/{lesson_id}")
def authorize_video(
    lesson_id: int,
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    """
    Secure video authorization endpoint.

    Verifies the authenticated user (Firebase JWT) has entitlement to view the lesson.
    If authorized, generates and returns a Bunny Stream signed playback URL.

    Security:
    - uid is extracted from verified Firebase JWT — cannot be spoofed
    - Free preview lessons skip the entitlement check
    - Paid lessons require an ACTIVE CourseEntitlement
    - The Bunny security key never leaves the server
    - Signed URLs expire in 1 hour (re-request required for continued playback)
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Free preview lessons are accessible to any authenticated user
    if not lesson.is_free_preview:
        entitlement = db.query(CourseEntitlement).filter(
            CourseEntitlement.user_id == uid,
            CourseEntitlement.course_id == lesson.course_id,
            CourseEntitlement.status == "ACTIVE",
        ).first()

        if not entitlement:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this lesson. "
                       "Purchase the course to unlock paid lessons.",
            )

    if not lesson.video_stream_id:
        raise HTTPException(
            status_code=404,
            detail="Video not yet available for this lesson",
        )

    # Generate Bunny Stream secure token (key stays server-side)
    token_data = VideoService.generate_bunny_secure_token(lesson.video_stream_id)

    return {
        "success": True,
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "is_free_preview": lesson.is_free_preview,
        "signed_url": token_data["signed_url"],
        "expires": token_data["expires"],
        "is_signed": token_data["is_signed"],
    }


@router.get("/preview/{lesson_id}")
def get_free_preview(
    lesson_id: int,
    uid: Optional[str] = Depends(get_optional_uid),
    db: Session = Depends(get_db),
):
    """
    Returns playback info for free preview lessons only.
    No entitlement check — accessible to unauthenticated users for marketing.
    Paid lessons return 403.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if not lesson.is_free_preview:
        raise HTTPException(
            status_code=403,
            detail="This lesson is not available as a free preview. Purchase the course to access it.",
        )

    if not lesson.video_stream_id:
        raise HTTPException(status_code=404, detail="Video not yet available for this lesson")

    token_data = VideoService.generate_bunny_secure_token(lesson.video_stream_id)

    return {
        "success": True,
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "is_free_preview": True,
        "signed_url": token_data["signed_url"],
        "expires": token_data["expires"],
        "is_signed": token_data["is_signed"],
    }
