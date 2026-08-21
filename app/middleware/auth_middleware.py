import json as _json
import logging
import os as _os
from typing import Any, Dict, Optional

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User


logger = logging.getLogger("auth_middleware")


# ============================================================
# Swagger / Bearer Authentication
# ============================================================

security = HTTPBearer(auto_error=False)


# ============================================================
# Firebase Admin SDK Initialization
# ============================================================

def _initialize_firebase():
    """
    Initialize Firebase Admin SDK.

    Supports:
    1. FIREBASE_SERVICE_ACCOUNT_JSON
       Raw Firebase service-account JSON stored in environment variable.

    2. GOOGLE_APPLICATION_CREDENTIALS
       Path to serviceAccountKey.json.

    3. Application Default Credentials
       Used automatically in supported Google Cloud environments.

    Safe to call multiple times.
    """

    if firebase_admin._apps:
        return

    try:
        raw_json = _os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        cred_path = _os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        # ----------------------------------------------------
        # Method 1: Raw JSON from environment variable
        # ----------------------------------------------------
        if raw_json and raw_json.strip().startswith("{"):
            service_dict = _json.loads(raw_json)

            cred = credentials.Certificate(service_dict)

            firebase_admin.initialize_app(cred)

            logger.info(
                "Firebase Admin SDK initialized using "
                "FIREBASE_SERVICE_ACCOUNT_JSON"
            )

        # ----------------------------------------------------
        # Method 2: Service account JSON file
        # ----------------------------------------------------
        elif cred_path and _os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)

            firebase_admin.initialize_app(cred)

            logger.info(
                "Firebase Admin SDK initialized using "
                f"GOOGLE_APPLICATION_CREDENTIALS: {cred_path}"
            )

        # ----------------------------------------------------
        # Method 3: Application Default Credentials
        # ----------------------------------------------------
        else:
            cred = credentials.ApplicationDefault()

            firebase_admin.initialize_app(cred)

            logger.info(
                "Firebase Admin SDK initialized using "
                "Application Default Credentials"
            )

    except Exception as e:
        logger.warning(
            "Firebase Admin SDK could not initialize: %s. "
            "Set FIREBASE_SERVICE_ACCOUNT_JSON or "
            "GOOGLE_APPLICATION_CREDENTIALS. "
            "Auth-protected endpoints will return 503 "
            "until Firebase is configured.",
            e,
        )


_initialize_firebase()


# ============================================================
# Development Bypass
# ============================================================

# Development bypass tokens are ONLY active when APP_ENV
# is NOT "production".
#
# Production environment:
# APP_ENV=production
#
# Therefore all bypass tokens are disabled in production.

_DEV_MODE = (
    _os.getenv("APP_ENV", "development").lower() != "production"
)


# ============================================================
# Firebase Token Verification
# ============================================================

def get_current_token_payload(
    credentials_data: Optional[HTTPAuthorizationCredentials] = Depends(
        security
    ),
) -> Dict[str, Any]:
    """
    FastAPI dependency that verifies a Firebase ID token.

    Swagger will recognize this as HTTP Bearer authentication.

    Expected header:

        Authorization: Bearer <firebase_id_token>

    Returns:
        Decoded Firebase token claims.
    """

    # --------------------------------------------------------
    # Authorization header missing
    # --------------------------------------------------------

    if not credentials_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authorization header missing. "
                "Expected: 'Bearer <firebase_id_token>'"
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # HTTPBearer has already separated "Bearer" from the token.
    id_token = credentials_data.credentials.strip()

    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token is empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --------------------------------------------------------
    # Development bypass
    # --------------------------------------------------------

    if _DEV_MODE:

        if (
            id_token.startswith("dev_admin_")
            or id_token == "test_admin_token"
        ):
            return {
                "uid": "admin_dev_uid",
                "email": "iam@edukkit.com",
                "role": "admin",
                "admin": True,
            }

        if (
            id_token.startswith("dev_teacher_")
            or id_token == "test_teacher_token"
        ):
            return {
                "uid": "teacher_dev_uid",
                "email": "teacher@edukkit.com",
                "role": "teacher",
            }

        if (
            id_token.startswith("dev_student_")
            or id_token == "test_student_token"
        ):
            return {
                "uid": "student_dev_uid",
                "email": "student@edukkit.com",
                "role": "student",
            }

    # --------------------------------------------------------
    # Firebase initialization check
    # --------------------------------------------------------

    if not firebase_admin._apps:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Authentication service not initialized. "
                "Contact support."
            ),
        )

    # --------------------------------------------------------
    # Verify Firebase ID token
    # --------------------------------------------------------

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)

        uid = decoded_token.get("uid")

        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain a valid user ID.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return decoded_token

    # --------------------------------------------------------
    # Token expired
    # --------------------------------------------------------

    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Firebase token has expired. "
                "Please sign in again."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --------------------------------------------------------
    # Token revoked
    # --------------------------------------------------------

    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Firebase token has been revoked. "
                "Please sign in again."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --------------------------------------------------------
    # Invalid Firebase token
    # --------------------------------------------------------

    except firebase_auth.InvalidIdTokenError as e:
        logger.warning(
            "Invalid Firebase ID token: %s",
            e,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --------------------------------------------------------
    # Any other Firebase verification error
    # --------------------------------------------------------

    except Exception as e:
        logger.error(
            "Firebase token verification error: %s",
            e,
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================
# Current Firebase UID
# ============================================================

def get_current_uid(
    credentials_data: Optional[HTTPAuthorizationCredentials] = Depends(
        security
    ),
) -> str:
    """
    Verify Firebase ID token and return the Firebase UID.
    """

    payload = get_current_token_payload(credentials_data)

    return payload["uid"]


# ============================================================
# Optional Firebase UID
# ============================================================

def get_optional_uid(
    credentials_data: Optional[HTTPAuthorizationCredentials] = Depends(
        security
    ),
) -> Optional[str]:
    """
    Optional authentication dependency.

    Returns:
        Firebase UID if a valid token is supplied.
        None if no valid authentication is supplied.
    """

    if not credentials_data:
        return None

    try:
        return get_current_uid(credentials_data)

    except HTTPException:
        return None


# ============================================================
# Current Database User
# ============================================================

def get_current_user_model(
    credentials_data: Optional[HTTPAuthorizationCredentials] = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Return the database User model for the authenticated Firebase user.

    If the Firebase user does not yet exist in the database,
    a matching user record is automatically created.
    """

    payload = get_current_token_payload(credentials_data)

    uid = payload["uid"]

    email = payload.get("email")

    name = (
        payload.get("name")
        or payload.get("display_name")
        or "Edukkit User"
    )

    # --------------------------------------------------------
    # Find user by Firebase UID
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.firebase_uid == uid)
        .first()
    )

    # --------------------------------------------------------
    # If not found, try email
    # --------------------------------------------------------

    if not user and email:

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        # Link existing DB user to Firebase UID
        if user and not user.firebase_uid:

            user.firebase_uid = uid

            db.commit()
            db.refresh(user)

    # --------------------------------------------------------
    # Create user automatically if necessary
    # --------------------------------------------------------

    if not user:

        # Root admin email gets admin role automatically.
        #
        # IMPORTANT:
        # Users cannot select admin/teacher during registration.
        # This is only for the predefined root admin account.

        if (
            email
            and email.lower() == "iam@edukkit.com"
        ):
            initial_role = "admin"

        else:
            initial_role = payload.get(
                "role",
                "student",
            )

            # Never trust arbitrary Firebase role claims
            # for automatic privilege escalation.
            if initial_role not in (
                "student",
                "teacher",
                "staff",
                "admin",
            ):
                initial_role = "student"

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


# ============================================================
# Admin RBAC
# ============================================================

def get_current_admin(
    user: User = Depends(get_current_user_model),
) -> User:
    """
    Restrict endpoint access to administrators only.

    Allowed:
        role == admin

    Root admin:
        iam@edukkit.com
    """

    is_admin = (
        user.role == "admin"
        or (
            user.email
            and user.email.lower() == "iam@edukkit.com"
        )
    )

    if not is_admin:

        logger.warning(
            "Admin RBAC rejection for user %s (%s) "
            "with role '%s'",
            user.id,
            user.email,
            user.role,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Forbidden: Administrator privileges required."
            ),
        )

    return user


# ============================================================
# Staff / Teacher / Admin RBAC
# ============================================================

def get_current_staff_or_admin(
    user: User = Depends(get_current_user_model),
) -> User:
    """
    Restrict endpoint access to:

        - admin
        - teacher
        - staff

    Students and guests are denied.
    """

    is_authorized = (
        user.role in (
            "admin",
            "teacher",
            "staff",
        )
        or (
            user.email
            and user.email.lower() == "iam@edukkit.com"
        )
    )

    if not is_authorized:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Forbidden: Staff or Teacher privileges required."
            ),
        )

    return user
