import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.security import decode_token

DB = Annotated[Session, Depends(get_db)]


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_optional_user(db: DB, authorization: Annotated[str | None, Header()] = None) -> User | None:
    token = _bearer(authorization)
    if not token:
        return None
    user_id = decode_token(token)
    if user_id is None:
        return None
    return db.get(User, user_id)


def get_current_user(db: DB, authorization: Annotated[str | None, Header()] = None) -> User:
    token = _bearer(authorization)
    user_id = decode_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    expected = get_settings().ADMIN_TOKEN
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="管理员令牌无效")


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
