from typing import Optional
from pydantic import BaseModel, EmailStr, constr, validator

from src.users.models import UserGroupEnum
from src.users.validators import validate_password_complexity


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=100)

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "StrongP@ssw0rd"
            }
        }

    @validator("password")
    def password_complexity(cls, v):
        validate_password_complexity(v)
        return v


class UserCreateSchema(BaseModel):
    email: EmailStr
    hashed_password: str
    group: UserGroupEnum = UserGroupEnum.USER
    is_active: Optional[bool] = False

    class Config:
        orm_mode = True


class ActivationRequestSchema(BaseModel):
    email: EmailStr


class ActivationConfirmSchema(BaseModel):
    token: str


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class AccessTokenSchema(BaseModel):
    access_token: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class LogoutSchema(BaseModel):
    refresh_token: str


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordMixin(BaseModel):
    new_password: constr(min_length=8)

    @validator("new_password")
    def password_complexity(cls, v):
        validate_password_complexity(v)
        return v


class PasswordResetConfirmSchema(PasswordMixin):
    token: str


class PasswordChangeSchema(PasswordMixin):
    old_password: str
