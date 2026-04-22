from dataclasses import dataclass

from app.models.enums import Role


SESSION_USER_ID_KEY = "user_id"
SESSION_ROLE_KEY = "role"
SESSION_LOGIN_AT_KEY = "logged_in_at"


@dataclass(slots=True)
class SessionPrincipal:
    user_id: int
    role: Role
    email: str
    name: str
