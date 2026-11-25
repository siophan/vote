from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.rules import SIGNUP_BONUS
from app.services.common import insert_ignore
from app.services.ledger import apply_delta, lock_user


def get_or_create_user(db: Session, openid: str, unionid: str | None = None) -> tuple[User, bool]:
    """Return (user, created). The signup bonus is granted exactly once, by
    whichever request actually inserted the row."""
    stmt = (
        insert_ignore(db, User)
        .values(openid=openid, unionid=unionid, nickname="银龄生活家", city="",
                district="", community="", flower_balance=0, growth_value=0)
        .on_conflict_do_nothing(index_elements=["openid"])
        .returning(User.id)
    )
    new_id = db.execute(stmt).scalar_one_or_none()
    if new_id is not None:
        user = lock_user(db, new_id)
        apply_delta(db, user, SIGNUP_BONUS, "signup_bonus", ref_type="user", ref_id=user.id)
        db.commit()
        return user, True
    db.commit()
    user = db.scalars(select(User).where(User.openid == openid)).one()
    return user, False
