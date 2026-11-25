from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.deps import DB, CurrentUser, OptionalUser
from app.errors import not_found
from app.models import Category, Event, FlowerLedger, Submission, User
from app.routers.common import Pagination
from app.rules import normalize_city
from app.schemas import FlowersIn, FlowersOut, LedgerPage, RankingOut, SubmissionIn, SubmissionOut
from app.services.presenters import ledger_out, submission_out
from app.services.submissions import SUBMISSION_NOT_FOUND, create_submission, send_flowers

router = APIRouter(tags=["submissions"])


@router.post("/submissions", response_model=SubmissionOut)
def post_submission(data: SubmissionIn, db: DB, user: CurrentUser) -> SubmissionOut:
    return submission_out(create_submission(db, user, data))


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: DB, user: OptionalUser) -> SubmissionOut:
    sub = db.get(Submission, submission_id)
    if sub is None or (sub.status != "approved" and (user is None or user.id != sub.user_id)):
        raise not_found(SUBMISSION_NOT_FOUND)
    return submission_out(sub)


@router.post("/submissions/{submission_id}/flowers", response_model=FlowersOut)
def post_flowers(submission_id: int, data: FlowersIn, db: DB, user: CurrentUser) -> FlowersOut:
    balance, count = send_flowers(db, user, submission_id, data.count)
    return FlowersOut(flower_balance=balance, submission_flower_count=count)


@router.get("/flowers/ledger", response_model=LedgerPage)
def flower_ledger(db: DB, user: CurrentUser, pg: Annotated[Pagination, Depends()]) -> LedgerPage:
    total = db.scalar(select(func.count()).select_from(FlowerLedger).where(FlowerLedger.user_id == user.id)) or 0
    entries = db.scalars(
        select(FlowerLedger).where(FlowerLedger.user_id == user.id)
        .order_by(FlowerLedger.id.desc()).offset(pg.offset).limit(pg.page_size)
    ).all()
    return LedgerPage(balance=user.flower_balance, items=[ledger_out(e) for e in entries], total=total)


@router.get("/rankings", response_model=list[RankingOut])
def rankings(db: DB, city: str | None = None, category: str | None = None, limit: int = 20) -> list[RankingOut]:
    limit = min(100, max(1, limit))
    stmt = (
        select(Submission)
        .join(User, User.id == Submission.user_id)
        .join(Event, Event.id == Submission.event_id)
        .where(Submission.status == "approved")
    )
    city = normalize_city(city)
    if city:
        stmt = stmt.where(User.city == city)
    if category and category != "全部":
        stmt = stmt.join(Category, Category.id == Event.category_id).where(Category.name == category)
    subs = db.scalars(
        stmt.order_by(Submission.flower_count.desc(), Submission.id.asc()).limit(limit)
    ).unique().all()
    return [
        RankingOut(
            rank=i + 1,
            submission_id=s.id,
            author_id=s.user_id,
            title=s.title,
            event_title=s.event.title,
            author_nickname=s.author.nickname,
            author_avatar_url=s.author.avatar_url,
            city=s.author.city,
            flower_count=s.flower_count,
        )
        for i, s in enumerate(subs)
    ]
