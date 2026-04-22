from typing import Annotated, Any, cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import SessionPrincipal
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User


DBSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_session_data(request: Request) -> dict[str, Any]:
    return request.session


def get_current_principal(request: Request) -> SessionPrincipal | None:
    return cast(SessionPrincipal | None, getattr(request.state, "principal", None))


def _load_current_user(request: Request, db: Session) -> User | None:
    principal = get_current_principal(request)
    if principal is None:
        return None

    statement = (
        select(User)
        .options(selectinload(User.vendor_profile))
        .where(User.id == principal.user_id, User.is_active.is_(True))
    )
    user = db.execute(statement).scalar_one_or_none()
    if user is None:
        request.session.clear()
        return None

    return user


def get_optional_current_user(request: Request, db: DBSession) -> User | None:
    return _load_current_user(request, db)


def get_current_user(request: Request, db: DBSession) -> User:
    user = _load_current_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


def require_roles(*allowed_roles: Role):
    def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
VendorUser = Annotated[User, Depends(require_roles(Role.VENDOR))]
EndUser = Annotated[User, Depends(require_roles(Role.USER))]
VendorOrAdminUser = Annotated[User, Depends(require_roles(Role.VENDOR, Role.ADMIN))]
