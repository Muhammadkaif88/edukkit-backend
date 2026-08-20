import hashlib
import hmac
import base64
import time
from typing import Dict, Any, Optional
from ..config import settings
import logging

logger = logging.getLogger("video_service")


class VideoService:

    @staticmethod
    def generate_bunny_secure_token(
        video_id: str,
        expiration_seconds: int = 3600,
    ) -> Dict[str, Any]:
        """
        Generates a Bunny Stream Secure Token for protected HLS playback.

        Bunny Token Auth algorithm (Standard plan):
          token = base64url( HMAC-SHA256(security_key, expiry_timestamp + "/" + video_id) )
          URL   = https://{cdn_hostname}/{video_id}/playlist.m3u8?token={token}&expires={expiry}

        The BUNNY_SECURITY_KEY is read from server config and NEVER sent to Flutter.

        :param video_id: The Bunny.net video GUID
        :param expiration_seconds: Token validity duration in seconds (default 1 hour)
        :return: Dict containing signed_url, token, expires, video_id
        """
        security_key = settings.BUNNY_SECURITY_KEY
        cdn_hostname = settings.BUNNY_CDN_HOSTNAME

        if not security_key or security_key == "bunnysign_test_key":
            logger.warning(
                "BUNNY_SECURITY_KEY is not configured. "
                "Returning unsigned URL — this is NOT production-safe. "
                "Set BUNNY_SECURITY_KEY in your .env file."
            )
            # Unsigned URL for development — valid only if token auth is disabled on the library
            unsigned_url = f"https://{cdn_hostname}/{video_id}/playlist.m3u8"
            return {
                "signed_url": unsigned_url,
                "token": None,
                "expires": None,
                "video_id": video_id,
                "cdn_hostname": cdn_hostname,
                "is_signed": False,
            }

        expires = int(time.time()) + expiration_seconds

        # Bunny Token Auth: HMAC-SHA256(key, expires + "/" + video_id)
        # Then base64url-encode the raw digest
        signing_string = f"{expires}/{video_id}"
        raw_digest = hmac.new(
            security_key.encode("utf-8"),
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        # Base64url encode (URL-safe, no padding)
        token = base64.urlsafe_b64encode(raw_digest).rstrip(b"=").decode("utf-8")

        signed_url = (
            f"https://{cdn_hostname}/{video_id}/playlist.m3u8"
            f"?token={token}&expires={expires}"
        )

        return {
            "signed_url": signed_url,
            "token": token,
            "expires": expires,
            "video_id": video_id,
            "cdn_hostname": cdn_hostname,
            "is_signed": True,
        }

    @staticmethod
    def generate_lesson_thumbnail_url(video_id: str) -> str:
        """Returns the public thumbnail URL for a Bunny Stream video."""
        cdn_hostname = settings.BUNNY_CDN_HOSTNAME
        return f"https://{cdn_hostname}/{video_id}/thumbnail.jpg"
