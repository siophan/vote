from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import bad_request, not_found
from app.models import Event, FlowerGift, Submission, User
from app.rules import (
    APPROVAL_BONUS,
    DAILY_GIFT_LIMIT_PER_AUTHOR,
    DUPLICATE_VIDEO_OTHER,
    DUPLICATE_VIDEO_OWN,
    VIDEO_LINK_ERROR,
    normalize_video_url,
    today_start_utc,
)
from app.schemas import FeedPatch, ReviewIn, SubmissionIn
from app.services.events import enroll, get_event_or_404
from app.services.ledger import apply_delta, lock_user, lock_users

SUBMISSION_NOT_FOUND = "作品不存在"
FEED_INFO_REQUIRED = "请填写视频 token，或视频号 ID 与 feed_id"
FEED_FIELDS = ("finder_user_name", "feed_id", "feed_token")
MIN_FLOWERS, MAX_FLOWERS = 1, 99


def ensure_video_unused(db: Session, video_url: str, user_id: int, exclude_id: int | None = None) -> None:
    """A video may back only one live (pending/approved) submission, across all
    users: resubmitting it would earn APPROVAL_BONUS again, and someone else's
    video is not yours to enter. A rejected submission frees the link."""
    stmt = select(Submission.user_id).where(Submission.video_url == video_url, Submission.status != "rejected")
    if exclude_id is not None:
        stmt = stmt.where(Submission.id != exclude_id)
    owner = db.scalars(stmt.limit(1)).first()
    if owner is not None:
        raise bad_request(DUPLICATE_VIDEO_OWN if owner == user_id else DUPLICATE_VIDEO_OTHER)


def ensure_feed_unused(db: Session, sub: Submission) -> None:
    """Short links for one video can differ between copies, so the link check
    can miss a repeat. The feed_id / feed_token that operators fill in while
    reviewing identify the video itself; refuse a second live submission of it."""
    clauses = []
    if sub.finder_user_name and sub.feed_id:
        clauses.append((Submission.finder_user_name == sub.finder_user_name) & (Submission.feed_id == sub.feed_id))
    if sub.feed_token:
        clauses.append(Submission.feed_token == sub.feed_token)
    if not clauses:
        return
    other = db.scalars(
        select(Submission.id).where(
            Submission.id != sub.id, Submission.status != "rejected", or_(*clauses)
        ).limit(1)
    ).first()
    if other is not None:
        raise bad_request(f"这条视频与作品 #{other} 是同一条视频，请驳回本条投稿")


def ensure_feed_info(sub: Submission) -> None:
    """An approved work must be playable in the mini-program (feed_token →
    <channel-video>, or finder_user_name + feed_id → openChannelsActivity), and
    the feed identity is what catches repeats whose short links differ."""
    if not (sub.feed_token or (sub.finder_user_name and sub.feed_id)):
        raise bad_request(FEED_INFO_REQUIRED)


def _apply_feed_fields(sub: Submission, values: dict) -> None:
    for field in FEED_FIELDS:
        value = values.get(field)
        if value is not None:
            setattr(sub, field, value.strip() or None)


def create_submission(db: Session, user: User, data: SubmissionIn) -> Submission:
    event = get_event_or_404(db, data.event_id)
    title = data.title.strip()
    if not title:
        raise bad_request("请填写作品标题")
    video_url = normalize_video_url(data.video_url)
    if video_url is None:
        raise bad_request(VIDEO_LINK_ERROR)
    ensure_video_unused(db, video_url, user.id)
    enroll(db, user, event)
    sub = Submission(
        user_id=user.id,
        event_id=event.id,
        title=title,
        description=(data.description or "").strip(),
        video_url=video_url,
        status="pending",
    )
    db.add(sub)
    try:
        db.commit()
    except IntegrityError:  # lost a race on uq_submissions_live_video
        db.rollback()
        raise bad_request(DUPLICATE_VIDEO_OWN) from None
    db.refresh(sub)
    return sub


def lock_submission(db: Session, submission_id: int) -> Submission:
    sub = db.scalars(
        select(Submission)
        .where(Submission.id == submission_id)
        .with_for_update(of=Submission)
        .execution_options(populate_existing=True)
    ).unique().one_or_none()
    if sub is None:
        raise not_found(SUBMISSION_NOT_FOUND)
    return sub


def review_submission(db: Session, submission_id: int, data: ReviewIn) -> Submission:
    sub = lock_submission(db, submission_id)
    _apply_feed_fields(sub, data.model_dump(include=set(FEED_FIELDS)))
    sub.reviewed_at = datetime.now(UTC)
    if data.action == "approve":
        if sub.status == "rejected":  # re-approving would re-occupy the link
            ensure_video_unused(db, sub.video_url, sub.user_id, exclude_id=sub.id)
        ensure_feed_info(sub)
        ensure_feed_unused(db, sub)
        sub.status = "approved"
        sub.reject_reason = None
        if not sub.approval_bonus_granted:
            author = lock_user(db, sub.user_id)
            apply_delta(db, author, APPROVAL_BONUS, "submission_approved",
                        ref_type="submission", ref_id=sub.id, growth=APPROVAL_BONUS)
            sub.approval_bonus_granted = True
    else:
        sub.status = "rejected"
        sub.reject_reason = (data.reason or "").strip() or "未通过审核"
    db.commit()
    db.refresh(sub)
    return sub


def update_feed_info(db: Session, submission_id: int, data: FeedPatch) -> Submission:
    """Fix the 视频号 info of a submission without changing its status."""
    sub = lock_submission(db, submission_id)
    _apply_feed_fields(sub, data.model_dump(exclude_unset=True))
    if sub.status == "approved":
        ensure_feed_info(sub)
    if sub.status != "rejected":
        ensure_feed_unused(db, sub)
    db.commit()
    db.refresh(sub)
    return sub


def send_flowers(db: Session, sender: User, submission_id: int, count: int) -> tuple[int, int]:
    """Returns (sender_balance, submission_flower_count)."""
    if not isinstance(count, int) or not (MIN_FLOWERS <= count <= MAX_FLOWERS):
        raise bad_request("每次可送 1–99 朵小红花")
    sub = db.get(Submission, submission_id)
    if sub is None or (sub.status != "approved" and sub.user_id != sender.id):
        raise not_found(SUBMISSION_NOT_FOUND)
    if sub.user_id == sender.id:
        raise bad_request("不能给自己的作品送花")
    if sub.status != "approved":
        raise bad_request("作品审核通过后才能送花")

    users = lock_users(db, sender.id, sub.user_id)
    giver, author = users[sender.id], users[sub.user_id]
    # Caps how fast flowers can be funnelled from throwaway accounts into one
    # author. The sender row is locked, so concurrent sends see each other.
    given_today = db.scalar(
        select(func.coalesce(func.sum(FlowerGift.count), 0)).where(
            FlowerGift.sender_id == giver.id,
            FlowerGift.receiver_id == author.id,
            FlowerGift.created_at >= today_start_utc(),
        )
    ) or 0
    remaining = DAILY_GIFT_LIMIT_PER_AUTHOR - given_today
    if count > remaining:
        if remaining <= 0:
            raise bad_request(f"今天已给这位作者送了 {DAILY_GIFT_LIMIT_PER_AUTHOR} 朵，明天再来支持吧")
        raise bad_request(f"每天给同一位作者最多送 {DAILY_GIFT_LIMIT_PER_AUTHOR} 朵，今天还能送 {remaining} 朵")
    apply_delta(db, giver, -count, "send_flower", ref_type="submission", ref_id=sub.id, growth=count)
    apply_delta(db, author, count, "receive_flower", ref_type="submission", ref_id=sub.id, growth=count)
    db.execute(
        update(Submission).where(Submission.id == sub.id)
        .values(flower_count=Submission.flower_count + count)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(Event).where(Event.id == sub.event_id)
        .values(flower_count=Event.flower_count + count)
        .execution_options(synchronize_session=False)
    )
    db.add(FlowerGift(sender_id=giver.id, receiver_id=author.id, submission_id=sub.id, count=count))
    db.commit()
    db.refresh(sub)
    return giver.flower_balance, sub.flower_count
