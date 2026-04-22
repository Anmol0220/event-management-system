from fastapi import APIRouter, Depends, Request, status

from app.core.csrf import enforce_csrf_protection
from app.core.dependencies import CurrentUser, DBSession, AppSettings
from app.schemas.auth import AuthResponse, AuthUserResponse, LoginRequest, LogoutResponse, SignupRequest
from app.services.auth import authenticate_user, clear_session, establish_session, register_user


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(enforce_csrf_protection)],
)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    request: Request,
    db: DBSession,
    settings: AppSettings,
) -> AuthResponse:
    user = register_user(db, settings, payload)
    establish_session(request, user)
    return AuthResponse(
        message="Signup successful.",
        user=AuthUserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: DBSession) -> AuthResponse:
    user = authenticate_user(db, payload)
    establish_session(request, user)
    return AuthResponse(
        message="Login successful.",
        user=AuthUserResponse.model_validate(user),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(request: Request) -> LogoutResponse:
    clear_session(request)
    return LogoutResponse(message="Logout successful.")


@router.get("/me", response_model=AuthUserResponse)
def get_authenticated_user(current_user: CurrentUser) -> AuthUserResponse:
    return AuthUserResponse.model_validate(current_user)
