from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from config.settings import settings


pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=14,
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using the configured password context.

    This function takes a plain-text password and returns its bcrypt hash.
    The bcrypt algorithm is used with a specified number of rounds for enhanced security.

    Args:
        password (str): The plain-text password to hash.

    Returns:
        str: The resulting hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against its hashed version.

    This function compares a plain-text password with a hashed password and returns True
    if they match, and False otherwise.

    Args:
        plain_password (str): The plain-text password provided by the user.
        hashed_password (str): The hashed password stored in the database.

    Returns:
        bool: True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with optional expiration time.

    This function generates a JWT token by encoding the provided data payload.
    It includes an expiration time ('exp' claim), either specified via `expires_delta` or
    taken from the default settings.

    Args:
        data (dict): The payload data to encode into the JWT token.
        expires_delta (timedelta | None): Optional expiration time. If not provided,
        the default expiration time from settings will be used.

    Returns:
        str: The encoded JWT access token as a string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode a JWT token and return the payload if valid.

    This function attempts to decode a JWT token using the configured secret key
    and algorithm. If the token is invalid or expired, it returns an empty dictionary.

    Args:
        token (str): The JWT token to decode.

    Returns:
        dict: The decoded token payload if successful, otherwise an empty dict.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if "sub" not in payload:
            raise JWTError("Token does not contain 'sub' field")
        return payload
    except JWTError as e:
        print(f"JWT Error: {e}")
        return {}
