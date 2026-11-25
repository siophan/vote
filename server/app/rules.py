"""Pure business rules: levels, reason texts, link validation, asset URLs."""

import re
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from app.config import get_settings

LEVELS: list[tuple[int, str]] = [
    (0, "银龄新人"),
    (300, "社区新星"),
    (1000, "银龄新星"),
    (3000, "龄花达人"),
    (8000, "龄花名家"),
]


def level_info(growth_value: int) -> tuple[str, str | None, int | None]:
    """Return (level_name, next_level_name, next_level_value)."""
    idx = 0
    for i, (threshold, _) in enumerate(LEVELS):
        if growth_value >= threshold:
            idx = i
    current = LEVELS[idx][1]
    if idx + 1 >= len(LEVELS):
        return current, None, None
    next_value, next_name = LEVELS[idx + 1]
    return current, next_name, next_value


REASON_TEXT = {
    "signup_bonus": "新人礼",
    "enroll_bonus": "报名奖励",
    "submission_approved": "投稿通过",
    "send_flower": "送出小红花",
    "receive_flower": "收到小红花",
    "redeem": "商城兑换",
    "refund": "订单退回",
    "admin_adjust": "运营调整",
}

ORDER_STATUS_TEXT = {
    "pending_shipment": "待发货",
    "shipped": "已发货",
    "completed": "已完成",
    "cancelled": "已取消",
}

SIGNUP_BONUS = 100
ENROLL_BONUS = 10
APPROVAL_BONUS = 50
GEO_LEVELS = 6

# Anti-farming limits. "Today" is the China calendar day (UTC+8, no DST).
ENROLL_BONUS_DAILY_LIMIT = 3  # enrollments per day that still earn ENROLL_BONUS
DAILY_GIFT_LIMIT_PER_AUTHOR = 20  # flowers one sender may give one author per day
CHINA_TZ = timezone(timedelta(hours=8))


def today_start_utc(now: datetime | None = None) -> datetime:
    """Start of the current China calendar day, as an aware UTC datetime."""
    local = (now or datetime.now(UTC)).astimezone(CHINA_TZ)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def normalize_city(value: str | None) -> str:
    """"杭州市" and "杭州" are the same city: drop a trailing 市 so the
    region picker's names match free-form ones."""
    city = (value or "").strip()
    if len(city) > 2 and city.endswith("市"):
        city = city[:-1]
    return city

VIDEO_LINK_ERROR = "请粘贴视频号视频链接（weixin.qq.com / channels.weixin.qq.com）"
DUPLICATE_VIDEO_OWN = "这条视频已经投过稿了，同一条视频只能参加一个赛事"
DUPLICATE_VIDEO_OTHER = "这条视频已被其他用户投稿，如有疑问请联系客服"
_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"'，。；、）)]+", re.IGNORECASE)


def _host_allowed(host: str) -> bool:
    return host == "weixin.qq.com" or host.endswith(".weixin.qq.com") or host == "finder.video.qq.com"


def normalize_video_url(raw: str) -> str | None:
    """Return the cleaned 视频号 link, or None if it is not acceptable.

    Accepts a bare URL, or share text containing exactly one URL (the
    WeChat "copy link" text sometimes carries a caption before the link).
    """
    text = (raw or "").strip()
    if not text:
        return None
    candidate = text
    if not re.fullmatch(r"\S+", text):
        found = _URL_IN_TEXT.findall(text)
        if len(found) != 1:
            return None
        candidate = found[0]
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() != "https" or not host or parts.username or parts.password:
        return None
    if port not in (None, 443):
        return None
    if not _host_allowed(host):
        return None
    # Canonical form so trivially different copies of one link compare equal:
    # lowercase scheme/host, no default port, no #fragment, no trailing "/".
    # Path and query are kept as-is (video ids are case-sensitive).
    path = parts.path.rstrip("/") if len(parts.path) > 1 else parts.path
    return urlunsplit(("https", host, path, parts.query, ""))


def asset_url(name: str | None) -> str | None:
    if not name:
        return None
    if name.startswith(("http://", "https://")):
        return name
    return get_settings().ASSET_BASE_URL + name.lstrip("/")


def upload_url(path: str) -> str:
    return get_settings().UPLOAD_BASE_URL + path.lstrip("/")
