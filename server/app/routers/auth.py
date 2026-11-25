from fastapi import APIRouter

from app.deps import DB
from app.errors import bad_request
from app.schemas import LoginIn, LoginOut
from app.security import create_token
from app.services.presenters import user_out
from app.services.users import get_or_create_user
from app.wechat import WechatLoginError, code2session

router = APIRouter(tags=["auth"])


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.post("/auth/login", response_model=LoginOut)
def login(data: LoginIn, db: DB) -> LoginOut:
    try:
        session = code2session(data.code, data.dev_openid)
    except WechatLoginError as exc:
        raise bad_request(str(exc)) from exc
    user, _ = get_or_create_user(db, session.openid, session.unionid)
    return LoginOut(token=create_token(user.id), user=user_out(db, user))
