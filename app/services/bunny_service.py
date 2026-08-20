"""
BunnyStreamService -- Server-Side Bunny Stream Management API Client
=====================================================================

Wraps the Bunny Stream REST API for admin video management operations.
The BUNNY_API_KEY is read exclusively from server config and is NEVER
returned to the Admin Web browser or Flutter clients.

Upload Architecture (TUS / direct-to-Bunny):
  For large video files, direct browser-to-Bunny upload is architecturally
  correct to avoid proxying gigabyte-scale files through the FastAPI server.

  Flow:
    1. Admin Web requests a signed upload session from FastAPI:
         POST /api/admin/videos/upload-session
    2. FastAPI calls Bunny to create a video object and returns:
         { video_id, upload_url, auth_signature, expires_at }
       NOTE: auth_signature is a short-lived HMAC -- the permanent API key
       is NEVER sent to the browser.
    3. Admin Web uploads the file directly to Bunny TUS endpoint using
       video_id + auth_signature.
    4. Admin Web calls FastAPI to link the finished video_id to a lesson:
         PATCH /api/admin/videos/{video_id}/link-lesson
    5. FastAPI updates Lesson.video_stream_id in the database.

All Bunny API errors are caught and re-raised as clean HTTPExceptions
without leaking API keys or internal Bunny error details.
"""

import hashlib
import hmac as _hmac
import time
import logging
from typing import Optional, Dict, Any

import httpx

from ..config import settings

logger = logging.getLogger("bunny_service")

# Bunny Stream API base URL
BUNNY_API_BASE = "https://video.bunnycdn.com"


class BunnyCredentialsError(Exception):
    """Raised when Bunny API credentials are not configured."""


class BunnyAPIError(Exception):
    """Raised when Bunny Stream API returns an error."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def _assert_api_key_configured() -> str:
    """Returns BUNNY_API_KEY or raises a clean error if not set."""
    key = settings.BUNNY_API_KEY
    if not key:
        raise BunnyCredentialsError(
            "BUNNY_API_KEY is not configured. "
            "Set BUNNY_API_KEY in your .env file. "
            "This value is the Video Library API key from Bunny.net dashboard."
        )
    return key


def _assert_library_id_configured() -> str:
    """Returns BUNNY_LIBRARY_ID or raises if still at placeholder."""
    lib_id = settings.BUNNY_LIBRARY_ID
    if not lib_id or lib_id == "123456":
        raise BunnyCredentialsError(
            "BUNNY_LIBRARY_ID is not configured. "
            "Set BUNNY_LIBRARY_ID in your .env file. "
            "This is the numeric library ID from your Bunny Stream library."
        )
    return lib_id


def _bunny_headers(api_key: str) -> Dict[str, str]:
    """Returns the standard Bunny Stream API request headers."""
    return {
        "AccessKey": api_key,
        "Content-Type": "application/json",
        "accept": "application/json",
    }


def _generate_upload_signature(video_id: str, expiry: int, api_key: str, library_id: str) -> str:
    """
    Generates the SHA256 HMAC signature required for Bunny TUS upload authentication.

    Algorithm: SHA256( library_id + api_key + expiry + video_id )
    This is a SHORT-LIVED signature. The permanent api_key is NEVER sent to the browser.
    """
    signing_string = f"{library_id}{api_key}{expiry}{video_id}"
    digest = hashlib.sha256(signing_string.encode("utf-8")).hexdigest()
    return digest


class BunnyStreamService:
    """
    Provides admin video management operations via Bunny Stream REST API.
    All methods are synchronous (httpx sync client) for FastAPI sync routes.
    """

    @staticmethod
    def create_video(title: str, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new video object in the Bunny Stream library.
        Returns the video object including the GUID (video_id) for TUS upload.
        """
        api_key = _assert_api_key_configured()
        library_id = _assert_library_id_configured()

        payload: Dict[str, Any] = {"title": title}
        if collection_id:
            payload["collectionId"] = collection_id

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{BUNNY_API_BASE}/library/{library_id}/videos",
                    json=payload,
                    headers=_bunny_headers(api_key),
                )
            if resp.status_code not in (200, 201):
                raise BunnyAPIError(
                    f"Bunny create video failed (HTTP {resp.status_code})",
                    status_code=502,
                )
            data = resp.json()
            return {
                "video_id": data.get("guid", data.get("videoId")),
                "title": data.get("title"),
                "status": data.get("status"),
                "collection_id": data.get("collectionId"),
                "created_at": data.get("dateUploaded"),
                "library_id": library_id,
            }
        except (BunnyAPIError, BunnyCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Bunny create_video error: {e}")
            raise BunnyAPIError("Bunny Stream create video request failed", 502)

    @staticmethod
    def create_upload_session(title: str, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a video object and generates a short-lived TUS upload authorization.

        The Admin Web browser uses:
          - upload_url: Bunny TUS endpoint to upload the file to
          - tus_headers: short-lived auth headers (api_key NEVER included)
          - video_id: to track status and link to lesson after completion

        TUS endpoint: https://video.bunnycdn.com/tusupload
        Required TUS headers from browser:
          AuthorizationSignature: <auth_signature>
          AuthorizationExpire: <expires_at>
          VideoId: <video_id>
          LibraryId: <library_id>
        """
        api_key = _assert_api_key_configured()
        library_id = _assert_library_id_configured()

        # Step 1: Create video object in Bunny
        video_data = BunnyStreamService.create_video(title, collection_id)
        video_id = video_data["video_id"]

        # Step 2: Generate short-lived upload signature (valid 1 hour)
        expires_at = int(time.time()) + 3600
        auth_signature = _generate_upload_signature(video_id, expires_at, api_key, library_id)

        return {
            "video_id": video_id,
            "title": title,
            "library_id": library_id,
            "upload_url": f"{BUNNY_API_BASE}/tusupload",
            "expires_at": expires_at,
            "tus_headers": {
                "AuthorizationSignature": auth_signature,
                "AuthorizationExpire": str(expires_at),
                "VideoId": video_id,
                "LibraryId": library_id,
            },
            "instructions": (
                "Upload your video file to 'upload_url' using the TUS protocol. "
                "Include all keys from 'tus_headers' as HTTP headers. "
                "After upload completes, call PATCH /api/admin/videos/{video_id}/link-lesson "
                "to associate this video with a lesson."
            ),
        }

    @staticmethod
    def get_video(video_id: str) -> Dict[str, Any]:
        """
        Retrieves full video details from Bunny Stream.

        Bunny status codes:
          0=created, 1=uploaded, 2=processing, 3=transcoding,
          4=finished, 5=error, 6=upload_failed
        """
        api_key = _assert_api_key_configured()
        library_id = _assert_library_id_configured()

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{BUNNY_API_BASE}/library/{library_id}/videos/{video_id}",
                    headers=_bunny_headers(api_key),
                )
            if resp.status_code == 404:
                raise BunnyAPIError(f"Video '{video_id}' not found in Bunny library", 404)
            if resp.status_code != 200:
                raise BunnyAPIError(f"Bunny get video failed (HTTP {resp.status_code})", 502)

            data = resp.json()
            cdn_hostname = settings.BUNNY_CDN_HOSTNAME

            STATUS_LABELS = {
                0: "created", 1: "uploaded", 2: "processing",
                3: "transcoding", 4: "finished", 5: "error", 6: "upload_failed",
            }
            status_code = data.get("status", -1)
            status_label = STATUS_LABELS.get(status_code, f"unknown({status_code})")

            return {
                "video_id": data.get("guid"),
                "title": data.get("title"),
                "status_code": status_code,
                "status": status_label,
                "is_ready": status_code == 4,
                "duration": data.get("length"),
                "size_bytes": data.get("storageSize"),
                "encode_progress": data.get("encodeProgress", 0),
                "thumbnail_url": (
                    f"https://{cdn_hostname}/{video_id}/thumbnail.jpg"
                    if status_code >= 1 else None
                ),
                "playback_url": (
                    f"https://{cdn_hostname}/{video_id}/playlist.m3u8"
                    if status_code == 4 else None
                ),
                "collection_id": data.get("collectionId"),
                "created_at": data.get("dateUploaded"),
                "library_id": library_id,
            }
        except (BunnyAPIError, BunnyCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Bunny get_video error for {video_id}: {e}")
            raise BunnyAPIError("Bunny Stream video status request failed", 502)

    @staticmethod
    def delete_video(video_id: str) -> Dict[str, Any]:
        """
        Permanently deletes a video from Bunny Stream.
        IRREVERSIBLE. Caller must unlink from lesson before calling.
        """
        api_key = _assert_api_key_configured()
        library_id = _assert_library_id_configured()

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.delete(
                    f"{BUNNY_API_BASE}/library/{library_id}/videos/{video_id}",
                    headers=_bunny_headers(api_key),
                )
            if resp.status_code == 404:
                raise BunnyAPIError(f"Video '{video_id}' not found -- already deleted?", 404)
            if resp.status_code not in (200, 204):
                raise BunnyAPIError(f"Bunny delete video failed (HTTP {resp.status_code})", 502)

            return {
                "success": True,
                "video_id": video_id,
                "message": f"Video '{video_id}' permanently deleted from Bunny Stream.",
            }
        except (BunnyAPIError, BunnyCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Bunny delete_video error for {video_id}: {e}")
            raise BunnyAPIError("Bunny Stream delete video request failed", 502)

    @staticmethod
    def list_videos(
        page: int = 1,
        per_page: int = 25,
        collection_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lists videos in the Bunny library with pagination."""
        api_key = _assert_api_key_configured()
        library_id = _assert_library_id_configured()

        params: Dict[str, Any] = {"page": page, "itemsPerPage": per_page}
        if collection_id:
            params["collection"] = collection_id
        if search:
            params["search"] = search

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{BUNNY_API_BASE}/library/{library_id}/videos",
                    params=params,
                    headers=_bunny_headers(api_key),
                )
            if resp.status_code != 200:
                raise BunnyAPIError(f"Bunny list videos failed (HTTP {resp.status_code})", 502)

            data = resp.json()
            items = data.get("items", [])
            cdn_hostname = settings.BUNNY_CDN_HOSTNAME

            STATUS_LABELS = {
                0: "created", 1: "uploaded", 2: "processing",
                3: "transcoding", 4: "finished", 5: "error", 6: "upload_failed",
            }

            return {
                "total": data.get("totalItems", len(items)),
                "page": page,
                "per_page": per_page,
                "videos": [
                    {
                        "video_id": v.get("guid"),
                        "title": v.get("title"),
                        "status": STATUS_LABELS.get(v.get("status", -1), "unknown"),
                        "is_ready": v.get("status") == 4,
                        "duration": v.get("length"),
                        "thumbnail_url": f"https://{cdn_hostname}/{v.get('guid')}/thumbnail.jpg",
                        "collection_id": v.get("collectionId"),
                        "created_at": v.get("dateUploaded"),
                    }
                    for v in items
                ],
            }
        except (BunnyAPIError, BunnyCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Bunny list_videos error: {e}")
            raise BunnyAPIError("Bunny Stream list videos request failed", 502)

    @staticmethod
    def validate_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
        """
        Validates incoming Bunny webhook requests using HMAC-SHA256.
        Returns True if valid; returns True (permissive) if BUNNY_WEBHOOK_SECRET not configured.
        """
        secret = settings.BUNNY_WEBHOOK_SECRET
        if not secret:
            logger.warning(
                "BUNNY_WEBHOOK_SECRET not configured -- webhook signature validation skipped. "
                "Set BUNNY_WEBHOOK_SECRET in .env for production-safe webhook validation."
            )
            return True

        expected = _hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return _hmac.compare_digest(expected, signature_header.lower())
