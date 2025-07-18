from pydantic import BaseModel, constr, EmailStr, field_validator

from ..validators import validate_password_complexity


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

    @field_validator("new_password")
    def password_complexity(cls, v):
        validate_password_complexity(v)
        return v


class PasswordResetConfirmSchema(PasswordMixin):
    token: str


class PasswordChangeSchema(PasswordMixin):
    old_password: str
