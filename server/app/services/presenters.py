"""Turn ORM rows into the contract shapes defined in docs/design.md."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Enrollment, Event, FlowerLedger, Order, Product, Submission, User
from app.rules import ORDER_STATUS_TEXT, REASON_TEXT, asset_url, level_info
from app.schemas import (
    Address,
    AuthorOut,
    EventOut,
    LedgerEntryOut,
    OrderOut,
    ProductOut,
    SubmissionOut,
    UserOut,
)


def aware(dt: datetime) -> datetime:
    """Normalise to UTC (SQLite returns naive datetimes, Postgres returns the session tz)."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def user_out(db: Session, user: User) -> UserOut:
    level_name, next_name, next_value = level_info(user.growth_value)
    enrolled = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == user.id)) or 0
    submitted = db.scalar(select(func.count()).select_from(Submission).where(Submission.user_id == user.id)) or 0
    return UserOut(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        city=user.city,
        district=user.district,
        community=user.community,
        flower_balance=user.flower_balance,
        growth_value=user.growth_value,
        level_name=level_name,
        next_level_name=next_name,
        next_level_value=next_value,
        enrolled_count=enrolled,
        submission_count=submitted,
        created_at=aware(user.created_at),
    )


def event_out(event: Event, enrolled: bool = False) -> EventOut:
    return EventOut(
        id=event.id,
        title=event.title,
        category=event.category.name,
        desc=event.desc,
        geo=event.geo,
        status_text=event.status_text,
        emoji=event.emoji,
        icon_key=event.icon_key,
        cover_url=asset_url(event.cover),
        heat=event.heat,
        participant_count=event.participant_count,
        flower_count=event.flower_count,
        reward_text=event.reward_text,
        ai_allowed=event.ai_allowed,
        ai_label=event.ai_label,
        track=event.track,
        video_status=event.video_status,
        enrolled=enrolled,
    )


def submission_out(sub: Submission) -> SubmissionOut:
    a = sub.author
    return SubmissionOut(
        id=sub.id,
        event_id=sub.event_id,
        event_title=sub.event.title,
        title=sub.title,
        description=sub.description,
        video_url=sub.video_url,
        finder_user_name=sub.finder_user_name,
        feed_id=sub.feed_id,
        feed_token=sub.feed_token,
        status=sub.status,
        reject_reason=sub.reject_reason,
        flower_count=sub.flower_count,
        author=AuthorOut(id=a.id, nickname=a.nickname, avatar_url=a.avatar_url, city=a.city),
        created_at=aware(sub.created_at),
    )


def ledger_out(entry: FlowerLedger) -> LedgerEntryOut:
    return LedgerEntryOut(
        id=entry.id,
        delta=entry.delta,
        reason=entry.reason,
        reason_text=REASON_TEXT.get(entry.reason, entry.reason),
        balance_after=entry.balance_after,
        note=entry.note,
        created_at=aware(entry.created_at),
    )


def product_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        name=p.name,
        subtitle=p.subtitle,
        reward_desc=p.reward_desc,
        category=p.category,
        kind=p.kind,
        price=p.price,
        image_url=asset_url(p.image),
        stock=p.stock,
        featured=p.featured,
    )


def order_out(o: Order) -> OrderOut:
    return OrderOut(
        id=o.id,
        product=product_out(o.product),
        quantity=o.quantity,
        total_price=o.total_price,
        status=o.status,
        status_text=ORDER_STATUS_TEXT.get(o.status, o.status),
        address=Address(**o.address) if o.address else None,
        tracking_no=o.tracking_no,
        created_at=aware(o.created_at),
    )
