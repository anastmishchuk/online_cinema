from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from src.users.models import UserGroupEnum


class UserProfileRead(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    avatar: Optional[str]
    date_of_birth: Optional[date]
    info: Optional[str]


class UserProfileUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    avatar: Optional[str]
    date_of_birth: Optional[date]
    info: Optional[str]


class UserReadSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    group: UserGroupEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('group', mode='before')
    @classmethod
    def serialize_group(cls, v):
        """Convert UserGroup object to enum value for response."""
        if hasattr(v, 'name'):
            return v.name
        return v

class RoleChangeSchema(BaseModel):
    new_role: UserGroupEnum
