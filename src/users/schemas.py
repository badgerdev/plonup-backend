# users/schemas.py
from pydantic import BaseModel, EmailStr, field_validator
import re
from typing import Optional, List
from datetime import datetime

from announcements.schemas import AnnouncementOutSchema

USERNAME_REGEX = r"^[a-zA-Z0-9_ ]+$"
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$"


# ---------------------------------------
# USER SCHEMAS
# ---------------------------------------
class SignupSchema(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOutSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_verified: bool
    is_deleted: bool
    delete_scheduled_for: Optional[datetime]


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if len(value) < 4:
            raise ValueError("Nazwa użytkownika musi mieć min. 4 znaki.")
        if len(value) > 20:
            raise ValueError("Nazwa użytkownika może mieć maks. 20 znaków.")
        if not re.match(USERNAME_REGEX, value):
            raise ValueError(
                "Nazwa użytkownika może zawierać tylko litery, cyfry, spacje i _"
            )
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if not re.match(PASSWORD_REGEX, value):
            raise ValueError(
                "Hasło musi mieć min. 8 znaków, dużą i małą literę, cyfrę i znak specjalny."
            )
        return value


class PublicUserProfileSchema(BaseModel):
    id: int
    username: str
    is_verified: bool
    average_rating: Optional[float] = 0.0
    announcements: List[AnnouncementOutSchema]


# ---------------------------------------
# REVIEW SCHEMAS
# ---------------------------------------
class ReviewInSchema(BaseModel):
    target_user_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Ocena musi być w skali 1–5.")
        return v


class ReviewOutSchema(BaseModel):
    id: int
    author_id: int
    author_username: str
    target_user_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime


# VERIFY SCHEMA


class VerifyEmailSchema(BaseModel):
    token: str


class PublicResendSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    password: str


class LoginSchema(BaseModel):
    username: str
    password: str


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str
