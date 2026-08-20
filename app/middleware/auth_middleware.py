import logging
from fastapi import Header, HTTPException, status, Depends
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from ..database import get_db
from ..models.user import User

logger = logging.getLogger("auth_middleware")


import json as _json
import os as _os

def _initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    Supports:
      1. FIREBASE_SERVICE_ACCOUNT_JSON (raw JSON string in env var)
      2. GOOGLE_APPLICATION_CREDENTIALS (file path to serviceAccountKey.json)
      3. Application Default Credentials (GCP environment)
    Safe to call multiple times — checks if already initialized.
    """
    if not firebase_admin._apps:
        try:
            raw_json = _os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            cred_path = _os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if raw_json and raw_json.strip().startswith("{"):
                service_dict = _json.loads(raw_json)
                cred = credentials.Certificate(service_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized via FIREBASE_SERVICE_ACCOUNT_JSON dict")
            elif cred_path and _os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Firebase Admin SDK initialized via Certificate({cred_path})")
            else:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized via Application Default Credentials")
        except Exception as e:
            logger.warning(
                f"Firebase Admin SDK could not initialize: {e}. "
                "Set GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON. "
                "Auth-protected endpoints will return 503 until configured."
            )


_initialize_firebase()


# Development bypass tokens — ONLY active when APP_ENV is not "production".
# Set APP_ENV=production in your hosting environment to disable all bypasses.
_DEV_MODE = _os.getenv("APP_ENV", "development").lower() != "production"

def get_current_token_payload(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency that decodes and verifies a Firebase ID Token from Authorization header.
    Returns the decoded token claims dictionary.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing. Expected: 'Bearer <firebase_id_token>'",
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: 'Bearer <token>'",
        )

    id_token = parts[1].strip()

    # Development bypass — active ONLY when APP_ENV != "production"
    if _DEV_MODE:
        if id_token.startswith("dev_admin_") or id_token == "test_admin_token":
            return {"uid": "admin_dev_uid", "email": "iam@edukkit.com", "role": "admin", "admin": True}
        if id_token.startswith("dev_teacher_") or id_token == "test_teacher_token":
            return {"uid": "teacher_dev_uid", "email": "teacher@edukkit.com", "role": "teacher"}
        if id_token.startswith("dev_student_") or id_token == "test_student_token":
            return {"uid": "student_dev_uid", "email": "student@edukkit.com", "role": "student"}

    if not firebase_admin._apps:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized. Contact support.",
        )

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token.get("uid")
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain a valid user ID",
            )
        return decoded_token
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token has expired. Please sign in again.",
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token has been revoked. Please sign in again.",
        )
    except firebase_auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Firebase token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
        )


def get_current_uid(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency that verifies a Firebase ID Token from the Authorization header.
    Returns verified Firebase UID string.
    """
    payload = get_current_token_payload(authorization)
    return payload["uid"]


def get_optional_uid(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Optional auth dependency — returns Firebase uid if a valid token is provided, else None.
    """
    if not authorization:
        return None
    try:
        return get_current_uid(authorization)
    except HTTPException:
        return None


def get_current_user_model(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that returns the database User model instance for the authenticated user.
    If the user does not exist in SQLite/PostgreSQL yet, automatically bootstraps the record.
    """
    payload = get_current_token_payload(authorization)
    uid = payload["uid"]
    email = payload.get("email")
    name = payload.get("name") or payload.get("display_name") or "Edukkit User"

    user = db.query(User).filter(User.firebase_uid == uid).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user and not user.firebase_uid:
            user.firebase_uid = uid
            db.commit()
            db.refresh(user)

    if not user:
        # Determine initial role: root admin email gets admin role automatically
        initial_role = "admin" if (email and email.lower() == "iam@edukkit.com") else payload.get("role", "student")
        user = User(
            firebase_uid=uid,
            email=email or f"{uid}@edukkit.local",
            name=name,
            role=initial_role,
            is_verified=True,
            approval_status="approved",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_current_admin(
    user: User = Depends(get_current_user_model),
) -> User:
    """
    RBAC Dependency: Restricts endpoint access strictly to Administrators.
    Raises HTTP 403 Forbidden for non-admin users.
    """
    is_admin = (
        user.role == "admin"
        or (user.email and user.email.lower() == "iam@edukkit.com")
    )
    if not is_admin:
        logger.warning(f"Admin RBAC rejection for user {user.id} ({user.email}) with role '{user.role}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrator privileges required.",
        )
    return user


def get_current_staff_or_admin(
    user: User = Depends(get_current_user_model),
) -> User:
    """
    RBAC Dependency: Restricts endpoint access to Staff, Teachers, and Administrators.
    Raises HTTP 403 Forbidden for students or guests.
    """
    is_authorized = (
        user.role in ("admin", "teacher", "staff")
        or (user.email and user.email.lower() == "iam@edukkit.com")
    )
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Staff or Teacher privileges required.",
        )
    return user
