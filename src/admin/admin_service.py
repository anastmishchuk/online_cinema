from jose import ExpiredSignatureError, JWTError
from sqlalchemy import select
from fastapi import Request

from src.config.database import AsyncSessionLocal
from src.users.models import UserGroupEnum, User
from src.users.utils.security import decode_token


async def check_admin_access(request: Request) -> bool:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return False

    token = auth[len("Bearer "):]
    try:
        payload = decode_token(token)
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            return False

        try:
            user_id = int(user_id_raw)
        except ValueError:
            return False

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalars().first()

        if not user:
            return False

        return user.group and user.group.name == UserGroupEnum.ADMIN

    except ExpiredSignatureError:
        print("Access token expired")
        return False

    except JWTError as e:
        print(f"JWT error: {e}")
        return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


async def check_admin_or_moderator_access(request: Request) -> bool:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return False

    token = auth[len("Bearer "):]
    try:
        payload = decode_token(token)
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            return False

        try:
            user_id = int(user_id_raw)
        except ValueError:
            return False

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalars().first()

        if not user:
            return False

        return user.group and user.group.name in (UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR)

    except ExpiredSignatureError:
        print("Access token expired")
        return False

    except JWTError as e:
        print(f"JWT error: {e}")
        return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
