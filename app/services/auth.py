from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth import SESSION_LOGIN_AT_KEY, SESSION_ROLE_KEY, SESSION_USER_ID_KEY
from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.crud.user import (
    create_user,
    create_vendor_profile,
    get_user_by_email,
    get_user_with_vendor_by_id,
    update_last_login,
)
from app.models.enums import Role
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest


def register_user(db: Session, settings: Settings, payload: SignupRequest) -> User:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if payload.role == Role.ADMIN:
        _validate_admin_signup(settings, payload.admin_signup_code)

    hashed_password = hash_password(payload.password)

    try:
        user = create_user(
            db,
            name=payload.name.strip(),
            email=payload.email,
            password=hashed_password,
            role=payload.role,
        )

        if payload.role == Role.VENDOR:
            create_vendor_profile(
                db,
                user_id=user.id,
                business_name=payload.business_name or payload.name,
                category_id=payload.category_id,
                contact_phone=payload.contact_phone,
                description=payload.vendor_description,
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    created_user = get_user_with_vendor_by_id(db, user.id)
    if created_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The account was created but could not be loaded.",
        )

    return created_user


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    try:
        update_last_login(db, user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    authenticated_user = get_user_with_vendor_by_id(db, user.id)
    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticated user could not be loaded.",
        )

    return authenticated_user


def establish_session(request: Request, user: User) -> None:
    request.session.clear()
    request.session[SESSION_USER_ID_KEY] = user.id
    request.session[SESSION_ROLE_KEY] = user.role.value
    request.session[SESSION_LOGIN_AT_KEY] = datetime.now(timezone.utc).isoformat()


def clear_session(request: Request) -> None:
    request.session.clear()


def _validate_admin_signup(settings: Settings, provided_code: str | None) -> None:
    if settings.allow_open_admin_signup:
        return

    if settings.admin_signup_code and provided_code == settings.admin_signup_code:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin signup is disabled or requires a valid admin signup code.",
    )
