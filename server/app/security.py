from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

ALGORITHM = "HS256"


def create_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=s.JWT_EXPIRE_DAYS)}
    return jwt.encode(payload, s.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, get_settings().JWT_SECRET, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
