"""Flower balance changes. Every change goes through `apply_delta`, which
writes a ledger row and refuses to drive a balance negative.

Callers must hold a row lock on the user (see `lock_user` / `lock_users`)
and commit the surrounding transaction themselves.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import bad_request
from app.models import FlowerLedger, User

INSUFFICIENT_BALANCE = "小红花余额不足"


def lock_user(db: Session, user_id: int) -> User:
    user = db.scalars(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    ).one()
    return user


def lock_users(db: Session, *user_ids: int) -> dict[int, User]:
    """Lock several users in ascending id order (avoids lock-order deadlocks)."""
    locked = {}
    for uid in sorted(set(user_ids)):
        locked[uid] = lock_user(db, uid)
    return locked


def apply_delta(
    db: Session,
    user: User,
    delta: int,
    reason: str,
    *,
    ref_type: str | None = None,
    ref_id: int | None = None,
    growth: int = 0,
) -> FlowerLedger:
    new_balance = user.flower_balance + delta
    if new_balance < 0:
        raise bad_request(INSUFFICIENT_BALANCE)
    user.flower_balance = new_balance
    if growth:
        user.growth_value = user.growth_value + growth
    entry = FlowerLedger(
        user_id=user.id,
        delta=delta,
        reason=reason,
        balance_after=new_balance,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(entry)
    db.flush()
    return entry
