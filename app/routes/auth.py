import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from firebase_admin import auth as firebase_auth

from ..database import get_db
from ..models.user import User
from ..schemas.auth_schema import RegisterRequest, AuthResponse
from ..middleware.auth_middleware import (
    _initialize_firebase,
    get_current_user_model,
)

logger = logging.getLogger("auth")

router = APIRouter()

# Make sure Firebase Admin SDK is initialized
_initialize_firebase()


@router.post(
    "/register",
    response_model=AuthResponse,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new Edukkit user.

    The user is created in Firebase Authentication and
    a matching PostgreSQL user record is created.
    """

    # Do not allow users to register themselves as admin/teacher.
    role = "student"

    # Check existing database user
    existing_user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        # Create Firebase Authentication user
        firebase_user = firebase_auth.create_user(
            email=data.email,
            password=data.password,
            display_name=data.name,
            email_verified=False,
        )

    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists in Firebase.",
        )

    except Exception as e:
        logger.error(f"Firebase registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create Firebase account.",
        )

    try:
        # Create matching database user
        user = User(
            firebase_uid=firebase_user.uid,
            email=data.email,
            name=data.name,
            phone=data.phone,
            role=role,
            approval_status="approved",
            is_verified=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    except Exception as e:
        db.rollback()

        # If database creation fails, remove the Firebase user
        try:
            firebase_auth.delete_user(firebase_user.uid)
        except Exception:
            logger.exception(
                "Failed to rollback Firebase user after DB failure"
            )

        logger.error(f"Database registration failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create user account.",
        )

    return AuthResponse(
        message="Registration successful. Please sign in with Firebase.",
        user_id=user.id,
        firebase_uid=user.firebase_uid,
        email=user.email,
        name=user.name,
        role=user.role,
        approval_status=user.approval_status,
        id_token=None,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    user: User = Depends(get_current_user_model),
):
    """
    Login / authenticate an existing Firebase user.

    The Flutter app must first sign in using Firebase Authentication
    and then send the Firebase ID token as:

        Authorization: Bearer <firebase_id_token>

    The backend verifies the token through get_current_user_model().
    """

    return AuthResponse(
        message="Login successful.",
        user_id=user.id,
        firebase_uid=user.firebase_uid,
        email=user.email,
        name=user.name,
        role=user.role,
        approval_status=user.approval_status,
        id_token=None,
    )
