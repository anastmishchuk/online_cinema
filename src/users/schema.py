from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, constr

from src.users.models import UserGroupEnum
from src.users.validators import validate_password_complexity


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "StrongP@ssw0rd"
            }
        }
    )

    @field_validator("password")
    def password_complexity(cls, v):
        validate_password_complexity(v)
        return v


class UserCreateSchema(BaseModel):
    email: EmailStr
    hashed_password: str
    group: UserGroupEnum = UserGroupEnum.USER
    is_active: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class UserReadSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    group: UserGroupEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("group", mode="before")
    @classmethod
    def extract_group_name(cls, v):
        # Extract the enum value from the UserGroup object
        if hasattr(v, 'name'):
            return v.name
        return v


class RoleChangeSchema(BaseModel):
    new_role: UserGroupEnum


class UserProfileRead(BaseModel):
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    avatar: Optional[str]
    date_of_birth: Optional[date]
    info: Optional[str]


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None
