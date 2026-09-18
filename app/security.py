import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured")

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30",
    )
)

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash(
    "dummy-password-for-timing-protection"
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

DbSession = Annotated[Session, Depends(get_db)]


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    stored_password_hash: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        stored_password_hash,
    )


def create_access_token(username: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:
    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if user is None:
        verify_password(password, DUMMY_HASH)
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    if not user.is_active:
        return None

    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        username = payload.get("sub")

        if not isinstance(username, str):
            raise credentials_exception

    except InvalidTokenError:
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user