"""WeChat mini-program code2session client."""

from dataclasses import dataclass

import httpx

from app.config import get_settings

CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
MOCK_OPENID = "mock_dev_user"


class WechatLoginError(Exception):
    pass


@dataclass
class WechatSession:
    openid: str
    unionid: str | None = None


def code2session(code: str, dev_openid: str | None = None) -> WechatSession:
    s = get_settings()
    if s.WECHAT_MOCK_LOGIN:
        return WechatSession(openid=(dev_openid or "").strip() or MOCK_OPENID)
    if not code:
        raise WechatLoginError("缺少登录凭证 code")
    if not s.WECHAT_APPID or not s.WECHAT_SECRET:
        raise WechatLoginError("服务端未配置微信登录")
    params = {
        "appid": s.WECHAT_APPID,
        "secret": s.WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        resp = httpx.get(CODE2SESSION_URL, params=params, timeout=8.0)
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WechatLoginError("微信登录失败，请稍后重试") from exc
    if data.get("errcode") or not data.get("openid"):
        raise WechatLoginError("微信登录失败，请重新进入小程序")
    # session_key is intentionally not persisted (not needed by current features).
    return WechatSession(openid=data["openid"], unionid=data.get("unionid"))
