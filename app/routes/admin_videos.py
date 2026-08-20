"""
Admin Video Management Routes — /api/admin/videos/*
====================================================

All endpoints require get_current_admin (role=admin).
No endpoint exposes the Bunny API key to the caller.

Upload flow:
  1. POST /api/admin/videos/upload-session
       Creates Bunny video object + returns short-lived TUS auth headers.
       Admin Web uploads directly to Bunny using those headers.

  2. GET  /api/admin/videos/{video_id}/status
       Poll until status == "finished".

  3. PATCH /api/admin/videos/{video_id}/link-lesson
       Stores video_id into Lesson.video_stream_id.

  4. DELETE /api/admin/videos/{video_id}
       Deletes from Bunny + optionally unlinks from lesson.

Webhook (optional, for automatic status updates):
  POST /api/admin/videos/webhook
       Validates Bunny HMAC signature, updates lesson status if needed.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.lesson import Lesson
from ..middleware.auth_middleware import get_current_admin
from ..models.user import User
from ..services.bunny_service import (
    BunnyStreamService,
    BunnyCredentialsError,
    BunnyAPIError,
)

logger = logging.getLogger("admin_videos")
router = APIRouter()


# ── Utility: map service exceptions to clean HTTP errors ─────────────────────

def _handle_bunny_error(e: Exception):
    """Converts BunnyCredentialsError / BunnyAPIError to FastAPI HTTPException.
    Credential errors return a generic 503 without leaking env var names or keys.
    """
    if isinstance(e, BunnyCredentialsError):
        # Log the full message server-side for the developer
        logger.error(f"Bunny credentials not configured: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Bunny Stream video service is not configured on this server. "
                "Contact your system administrator to configure video credentials."
            ),
        )
    if isinstance(e, BunnyAPIError):
        raise HTTPException(
            status_code=e.status_code,
            detail=str(e),
        )
    logger.error(f"Unexpected video management error: {e}")
    raise HTTPException(status_code=500, detail="Internal video management error.")


# ── 1. Create Upload Session ─────────────────────────────────────────────────

@router.post("/upload-session", status_code=status.HTTP_201_CREATED)
def create_video_upload_session(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Creates a Bunny video object and returns a short-lived TUS upload session.

    Request body:
      { "title": "Lesson 3 — Introduction to Circuits", "collection_id": "optional-uuid" }

    Response includes:
      - video_id: Bunny GUID for this video
      - upload_url: TUS endpoint for direct browser upload
      - tus_headers: Short-lived auth headers (NO permanent API key included)
      - expires_at: UNIX timestamp when upload auth expires (1 hour)
      - instructions: How to use the response

    The Admin Web must use these tus_headers when uploading directly to Bunny.
    After upload completes, call PATCH /api/admin/videos/{video_id}/link-lesson.
    """
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="'title' is required.")

    collection_id = body.get("collection_id")

    try:
        session_data = BunnyStreamService.create_upload_session(
            title=title,
            collection_id=collection_id,
        )
    except Exception as e:
        _handle_bunny_error(e)

    # Log creation (no secrets logged)
    logger.info(
        f"Admin {admin.email} created upload session for video_id={session_data['video_id']} "
        f"title='{title}'"
    )

    return session_data


# ── 2. Get Video Status ───────────────────────────────────────────────────────

@router.get("/{video_id}/status")
def get_video_status(
    video_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Returns current processing status for a Bunny video.

    Poll this endpoint after upload to check when status becomes 'finished'.
    Also returns whether this video is currently linked to any lesson.

    Bunny status values: created | uploaded | processing | transcoding | finished | error | upload_failed
    """
    try:
        video_data = BunnyStreamService.get_video(video_id)
    except Exception as e:
        _handle_bunny_error(e)

    # Check if this video is linked to any lesson in our DB
    lesson = db.query(Lesson).filter(Lesson.video_stream_id == video_id).first()
    video_data["linked_lesson"] = (
        {
            "lesson_id": lesson.id,
            "lesson_title": lesson.title,
            "course_id": lesson.course_id,
        }
        if lesson else None
    )

    return video_data


# ── 3. Get Full Video Details ─────────────────────────────────────────────────

@router.get("/{video_id}")
def get_video_detail(
    video_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Returns full video details from Bunny Stream plus DB lesson linkage info.
    No Bunny API key or permanent credentials are included in the response.
    """
    try:
        video_data = BunnyStreamService.get_video(video_id)
    except Exception as e:
        _handle_bunny_error(e)

    lesson = db.query(Lesson).filter(Lesson.video_stream_id == video_id).first()
    video_data["linked_lesson"] = (
        {
            "lesson_id": lesson.id,
            "lesson_title": lesson.title,
            "course_id": lesson.course_id,
            "is_free_preview": lesson.is_free_preview,
        }
        if lesson else None
    )

    return video_data


# ── 4. List Library Videos ────────────────────────────────────────────────────

@router.get("/")
def list_library_videos(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, le=100),
    collection_id: Optional[str] = None,
    search: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Lists all videos in the Bunny Stream library with pagination.
    Optionally filter by collection or search term.
    """
    try:
        result = BunnyStreamService.list_videos(
            page=page,
            per_page=per_page,
            collection_id=collection_id,
            search=search,
        )
    except Exception as e:
        _handle_bunny_error(e)

    # Annotate each video with its linked lesson (if any)
    video_ids = [v["video_id"] for v in result["videos"] if v["video_id"]]
    linked_lessons = (
        db.query(Lesson).filter(Lesson.video_stream_id.in_(video_ids)).all()
        if video_ids else []
    )
    lesson_map = {l.video_stream_id: {"lesson_id": l.id, "lesson_title": l.title, "course_id": l.course_id}
                  for l in linked_lessons}

    for v in result["videos"]:
        v["linked_lesson"] = lesson_map.get(v["video_id"])

    return result


# ── 5. Link Video to Lesson ───────────────────────────────────────────────────

@router.patch("/{video_id}/link-lesson")
def link_video_to_lesson(
    video_id: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Associates a Bunny video GUID with a lesson record in the database.

    Request body:
      { "lesson_id": 42 }

    This sets Lesson.video_stream_id = video_id.
    Existing lessons with a different video_id will be updated only when
    overwrite=true is included in the body.
    Existing video IDs are preserved unless explicitly overwritten.

    Does NOT delete any existing Bunny video — manage deletion separately.
    """
    lesson_id = body.get("lesson_id")
    if not lesson_id:
        raise HTTPException(status_code=400, detail="'lesson_id' is required.")

    lesson = db.query(Lesson).filter(Lesson.id == int(lesson_id)).first()
    if not lesson:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found.")

    # Safety: warn if lesson already has a video_id (but don't block)
    overwrite = bool(body.get("overwrite", False))
    existing_video_id = lesson.video_stream_id

    if existing_video_id and existing_video_id != video_id and not overwrite:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Lesson {lesson_id} already has video_id='{existing_video_id}'. "
                f"Pass 'overwrite': true to replace it. "
                f"Note: the old Bunny video is NOT automatically deleted — "
                f"delete it manually via DELETE /api/admin/videos/{existing_video_id} if needed."
            ),
        )

    lesson.video_stream_id = video_id
    db.commit()
    db.refresh(lesson)

    logger.info(
        f"Admin {admin.email} linked video_id='{video_id}' to lesson_id={lesson.id} "
        f"(previous: '{existing_video_id or 'none'}')"
    )

    return {
        "success": True,
        "video_id": video_id,
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "course_id": lesson.course_id,
        "previous_video_id": existing_video_id,
        "message": f"Video '{video_id}' successfully linked to lesson '{lesson.title}'.",
    }


# ── 6. Unlink Video from Lesson ───────────────────────────────────────────────

@router.patch("/{video_id}/unlink-lesson")
def unlink_video_from_lesson(
    video_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Removes the video_stream_id association from a lesson (sets it to NULL).
    Does NOT delete the Bunny video — use DELETE /api/admin/videos/{video_id} for that.
    """
    lesson = db.query(Lesson).filter(Lesson.video_stream_id == video_id).first()
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail=f"No lesson is currently linked to video_id='{video_id}'.",
        )

    lesson.video_stream_id = None
    db.commit()

    logger.info(f"Admin {admin.email} unlinked video_id='{video_id}' from lesson_id={lesson.id}")

    return {
        "success": True,
        "video_id": video_id,
        "unlinked_lesson_id": lesson.id,
        "message": f"Video unlinked from lesson '{lesson.title}'. Bunny video NOT deleted.",
    }


# ── 7. Delete Bunny Video ─────────────────────────────────────────────────────

@router.delete("/{video_id}")
def delete_bunny_video(
    video_id: str,
    unlink_lesson: bool = Query(default=True, description="Also unlink from lesson if linked"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Permanently deletes a video from Bunny Stream.

    IRREVERSIBLE. The video and all its transcoded versions are deleted.

    If unlink_lesson=true (default), also sets Lesson.video_stream_id = NULL
    for any lesson that was linked to this video.
    """
    # Check and optionally unlink lesson first
    linked_lesson = None
    lesson = db.query(Lesson).filter(Lesson.video_stream_id == video_id).first()
    if lesson:
        if unlink_lesson:
            lesson.video_stream_id = None
            db.commit()
            linked_lesson = {"lesson_id": lesson.id, "lesson_title": lesson.title}
            logger.info(
                f"Admin {admin.email} unlinked lesson {lesson.id} before deleting video '{video_id}'"
            )
        else:
            # Still delete Bunny video but leave lesson reference (will be a broken link)
            logger.warning(
                f"Deleting video '{video_id}' without unlinking lesson {lesson.id} "
                f"(unlink_lesson=false). Lesson will have a broken video reference."
            )

    try:
        result = BunnyStreamService.delete_video(video_id)
    except Exception as e:
        # If delete failed, re-link lesson
        if lesson and unlink_lesson:
            lesson.video_stream_id = video_id
            db.commit()
        _handle_bunny_error(e)

    logger.info(f"Admin {admin.email} permanently deleted Bunny video '{video_id}'")

    result["unlinked_lesson"] = linked_lesson
    return result


# ── 8. Bunny Webhook — Processing Status Callback ─────────────────────────────

@router.post("/webhook")
async def bunny_video_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives Bunny Stream processing status webhook callbacks.

    Validates the HMAC-SHA256 signature from Bunny (X-BunnyCDN-Signature header).
    If a video finishes processing, logs the event. No lesson auto-linking here
    (linking is done explicitly by admin after reviewing the finished video).

    Configure this URL in your Bunny Stream library settings:
      https://api.edukkit.com/api/admin/videos/webhook

    Note: This endpoint does NOT require admin authentication since Bunny calls
    it server-to-server. Authentication is via HMAC signature validation instead.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-BunnyCDN-Signature", "")

    if not BunnyStreamService.validate_webhook_signature(raw_body, signature):
        logger.warning("Bunny webhook received with invalid HMAC signature — rejected")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature.",
        )

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in webhook body.")

    video_id = payload.get("VideoGuid") or payload.get("videoId")
    event_type = payload.get("EventType", "unknown")
    video_status = payload.get("Status")

    STATUS_LABELS = {
        0: "created", 1: "uploaded", 2: "processing",
        3: "transcoding", 4: "finished", 5: "error", 6: "upload_failed",
    }
    status_label = STATUS_LABELS.get(video_status, str(video_status))

    logger.info(
        f"Bunny webhook: video_id={video_id} event={event_type} status={status_label}"
    )

    # If the video finished processing, note which lesson is linked (if any)
    linked_lesson_id = None
    if video_id and video_status == 4:
        lesson = db.query(Lesson).filter(Lesson.video_stream_id == video_id).first()
        if lesson:
            linked_lesson_id = lesson.id
            logger.info(
                f"Bunny webhook: video '{video_id}' finished processing — "
                f"linked to lesson {lesson.id} ('{lesson.title}')"
            )

    return {
        "received": True,
        "video_id": video_id,
        "event_type": event_type,
        "status": status_label,
        "linked_lesson_id": linked_lesson_id,
    }
