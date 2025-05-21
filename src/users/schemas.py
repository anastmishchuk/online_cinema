from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr

from models import UserGroupEnum


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

    class Config:
        orm_mode = True


class RoleChangeSchema(BaseModel):
    new_role: UserGroupEnum
