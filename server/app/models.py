from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("flower_balance >= 0", name="flower_balance_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    unionid: Mapped[str | None] = mapped_column(String(64))
    nickname: Mapped[str] = mapped_column(String(40), nullable=False, default="银龄生活家")
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    district: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    community: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    flower_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    growth_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    note: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    icon_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    image: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    reward_text: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True, nullable=False)
    desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    geo: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    status_text: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    icon_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    # Either a bare file name under ASSET_BASE_URL, or an absolute URL.
    cover: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    heat: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reward_text: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    ai_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_label: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    track: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    video_status: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    category: Mapped[Category] = relationship(lazy="joined", innerjoin=True)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_enrollments_user_event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


LIVE_SUBMISSION = text("status <> 'rejected'")


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"
    # One video backs at most one live submission (see ensure_video_unused).
    __table_args__ = (
        Index("uq_submissions_live_video", "video_url", unique=True,
              postgresql_where=LIVE_SUBMISSION, sqlite_where=LIVE_SUBMISSION),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    finder_user_name: Mapped[str | None] = mapped_column(String(100))
    feed_id: Mapped[str | None] = mapped_column(String(200))
    feed_token: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    flower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_bonus_granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    event: Mapped[Event] = relationship(lazy="joined", innerjoin=True)


class FlowerGift(Base):
    __tablename__ = "flower_gifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FlowerLedger(Base):
    __tablename__ = "flower_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("stock >= 0", name="stock_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    reward_desc: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="goods")
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    image: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=999)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    address: Mapped[dict | None] = mapped_column(JSON)
    tracking_no: Mapped[str | None] = mapped_column(String(64))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    product: Mapped[Product] = relationship(lazy="joined", innerjoin=True)
    user: Mapped[User] = relationship(lazy="joined", innerjoin=True)
