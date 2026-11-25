from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.errors import not_found
from app.models import Enrollment, Event, FlowerLedger, User
from app.rules import ENROLL_BONUS, ENROLL_BONUS_DAILY_LIMIT, today_start_utc
from app.services.common import insert_ignore
from app.services.ledger import apply_delta, lock_user

EVENT_NOT_FOUND = "赛事不存在"


def get_event_or_404(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise not_found(EVENT_NOT_FOUND)
    return event


def enrolled_event_ids(db: Session, user: User | None, event_ids: list[int] | None = None) -> set[int]:
    if user is None:
        return set()
    stmt = select(Enrollment.event_id).where(Enrollment.user_id == user.id)
    if event_ids is not None:
        stmt = stmt.where(Enrollment.event_id.in_(event_ids))
    return set(db.scalars(stmt))


def enroll(db: Session, user: User, event: Event) -> tuple[bool, int]:
    """Enroll `user` in `event`. Returns (first_time, bonus). Only the first
    enrollment counts towards participant_count, and only the first
    ENROLL_BONUS_DAILY_LIMIT of those per China day earn ENROLL_BONUS, so
    enrolling in every event at once cannot farm flowers. Does not commit."""
    stmt = (
        insert_ignore(db, Enrollment)
        .values(user_id=user.id, event_id=event.id)
        .on_conflict_do_nothing(index_elements=["user_id", "event_id"])
        .returning(Enrollment.id)
    )
    enrollment_id = db.execute(stmt).scalar_one_or_none()
    if enrollment_id is None:
        return False, 0
    db.execute(
        update(Event)
        .where(Event.id == event.id)
        .values(participant_count=Event.participant_count + 1)
        .execution_options(synchronize_session=False)
    )
    locked = lock_user(db, user.id)  # serializes the daily count per user
    rewarded_today = db.scalar(
        select(func.count()).select_from(FlowerLedger).where(
            FlowerLedger.user_id == user.id,
            FlowerLedger.reason == "enroll_bonus",
            FlowerLedger.created_at >= today_start_utc(),
        )
    ) or 0
    bonus = 0
    if rewarded_today < ENROLL_BONUS_DAILY_LIMIT:
        bonus = ENROLL_BONUS
        apply_delta(db, locked, bonus, "enroll_bonus", ref_type="event", ref_id=event.id, growth=bonus)
    db.refresh(event)
    return True, bonus
