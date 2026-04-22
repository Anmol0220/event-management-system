from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import Role, VendorStatus
from app.utils.sanitization import (
    sanitize_multiline_text,
    sanitize_single_line_text,
    validate_password_strength,
)


class VendorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_name: str
    contact_phone: str | None
    description: str | None
    category_id: int | None
    status: VendorStatus
    created_at: datetime
    updated_at: datetime


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    vendor_profile: VendorProfileResponse | None = None


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)
    confirm_password: str = Field(..., min_length=10, max_length=128)
    role: Role = Role.USER
    admin_signup_code: str | None = Field(default=None, max_length=255)
    business_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=30)
    vendor_description: str | None = Field(default=None, max_length=2000)
    category_id: int | None = Field(default=None, gt=0)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.strip().lower()

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        sanitized = sanitize_single_line_text(value)
        if sanitized is None:
            raise ValueError("Name is required.")
        return sanitized

    @field_validator("admin_signup_code", "business_name", "contact_phone")
    @classmethod
    def sanitize_optional_single_line_fields(cls, value: str | None) -> str | None:
        return sanitize_single_line_text(value)

    @field_validator("vendor_description")
    @classmethod
    def sanitize_optional_multiline_fields(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)

    @field_validator("confirm_password")
    @classmethod
    def keep_confirm_password_trimmed(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Confirm password is required.")
        return stripped

    @field_validator("password")
    @classmethod
    def keep_password_trimmed(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Password is required.")
        return validate_password_strength(stripped)

    @field_validator("admin_signup_code", mode="before")
    @classmethod
    def coerce_empty_admin_code_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_signup(self) -> "SignupRequest":
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password must match.")

        if self.role == Role.VENDOR and not self.business_name:
            raise ValueError("Business name is required for vendor signup.")

        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def sanitize_login_password(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Password is required.")
        return stripped


class AuthResponse(BaseModel):
    message: str
    user: AuthUserResponse


class LogoutResponse(BaseModel):
    message: str
