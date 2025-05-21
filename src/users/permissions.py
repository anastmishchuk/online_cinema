from fastapi import Depends, HTTPException, status
from .dependencies import get_current_user
from .models import User, UserGroupEnum


def require_role(required_roles: list[UserGroupEnum]):
    def role_checker(user: User = Depends(get_current_user)):
        if user.group not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker


is_user = require_role([UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN])
is_moderator = require_role([UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN])
is_admin = require_role([UserGroupEnum.ADMIN])
