from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


# ---------- requests ----------


class LoginIn(BaseModel):
    code: str = ""
    dev_openid: str | None = None


class MePatch(BaseModel):
    nickname: str | None = Field(default=None, max_length=40)
    avatar_url: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=40)
    district: str | None = Field(default=None, max_length=40)
    community: str | None = Field(default=None, max_length=80)


class SubmissionIn(BaseModel):
    event_id: int
    title: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    video_url: str = Field(max_length=1000)


class FlowersIn(BaseModel):
    count: int = 1


class Address(BaseModel):
    name: str = Field(default="", max_length=40)
    phone: str = Field(default="", max_length=20)
    province: str = Field(default="", max_length=40)
    city: str = Field(default="", max_length=40)
    district: str = Field(default="", max_length=40)
    detail: str = Field(default="", max_length=200)


class OrderIn(BaseModel):
    product_id: int
    quantity: int = 1
    address: Address | None = None


class ReviewIn(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=200)
    finder_user_name: str | None = Field(default=None, max_length=100)
    feed_id: str | None = Field(default=None, max_length=200)
    feed_token: str | None = Field(default=None, max_length=1000)


class FeedPatch(BaseModel):
    finder_user_name: str | None = Field(default=None, max_length=100)
    feed_id: str | None = Field(default=None, max_length=200)
    feed_token: str | None = Field(default=None, max_length=1000)


class AdjustIn(BaseModel):
    delta: int = Field(ge=-100000, le=100000)
    note: str = Field(max_length=200)

    @field_validator("delta")
    @classmethod
    def _nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("调整数量不能为 0")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("请填写调整备注")
        return v


class ShipIn(BaseModel):
    tracking_no: str | None = Field(default=None, max_length=64)


class EventPatch(BaseModel):
    heat: int | None = None
    participant_count: int | None = Field(default=None, ge=0)
    flower_count: int | None = Field(default=None, ge=0)
    reward_text: str | None = Field(default=None, max_length=100)
    ai_allowed: bool | None = None
    ai_label: str | None = Field(default=None, max_length=40)
    track: str | None = Field(default=None, max_length=100)
    video_status: str | None = Field(default=None, max_length=40)
    cover_url: str | None = Field(default=None, max_length=500)
    featured: bool | None = None


# ---------- responses ----------


class UserOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None
    city: str
    district: str
    community: str
    flower_balance: int
    growth_value: int
    level_name: str
    next_level_name: str | None
    next_level_value: int | None
    enrolled_count: int
    submission_count: int
    created_at: datetime


class LoginOut(BaseModel):
    token: str
    user: UserOut


class AvatarOut(BaseModel):
    avatar_url: str


class CategoryOut(BaseModel):
    name: str
    note: str
    icon_key: str
    image_url: str | None
    event_count: int


class SummaryOut(BaseModel):
    event_count: int
    category_count: int
    geo_levels: int


class EventOut(BaseModel):
    id: int
    title: str
    category: str
    desc: str
    geo: str
    status_text: str
    emoji: str
    icon_key: str
    cover_url: str | None
    heat: int
    participant_count: int
    flower_count: int
    reward_text: str
    ai_allowed: bool
    ai_label: str
    track: str
    video_status: str
    enrolled: bool


class EnrollOut(BaseModel):
    enrolled: bool
    first_time: bool
    bonus: int  # flowers granted by this call: ENROLL_BONUS, or 0 (repeat / daily limit reached)
    participant_count: int
    flower_balance: int


class AuthorOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None
    city: str


class SubmissionOut(BaseModel):
    id: int
    event_id: int
    event_title: str
    title: str
    description: str
    video_url: str
    finder_user_name: str | None
    feed_id: str | None
    feed_token: str | None
    status: str
    reject_reason: str | None
    flower_count: int
    author: AuthorOut
    created_at: datetime


class FlowersOut(BaseModel):
    flower_balance: int
    submission_flower_count: int


class LedgerEntryOut(BaseModel):
    id: int
    delta: int
    reason: str
    reason_text: str
    balance_after: int
    note: str | None = None
    created_at: datetime


class LedgerPage(BaseModel):
    balance: int
    items: list[LedgerEntryOut]
    total: int


class RankingOut(BaseModel):
    rank: int
    submission_id: int
    author_id: int
    title: str
    event_title: str
    author_nickname: str
    author_avatar_url: str | None
    city: str
    flower_count: int


class ProductOut(BaseModel):
    id: int
    name: str
    subtitle: str
    reward_desc: str
    category: str
    kind: str
    price: int
    image_url: str | None
    stock: int
    featured: bool


class OrderOut(BaseModel):
    id: int
    product: ProductOut
    quantity: int
    total_price: int
    status: str
    status_text: str
    address: Address | None
    tracking_no: str | None
    created_at: datetime


# ---------- admin ----------


class AdminUserOut(UserOut):
    openid: str


class EventAdminOut(EventOut):
    featured: bool
    sort_order: int


class OrderAdminOut(OrderOut):
    user_id: int
    user_nickname: str


class StatsOut(BaseModel):
    pending_submissions: int
    pending_shipments: int
    users_today: int
    flowers_today: int
