from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.deps import DB, CurrentUser, OptionalUser
from app.models import Category, Event, Submission
from app.rules import GEO_LEVELS, asset_url
from app.routers.common import Pagination
from app.schemas import CategoryOut, EnrollOut, EventOut, Page, SubmissionOut, SummaryOut
from app.services.events import enroll, enrolled_event_ids, get_event_or_404
from app.services.presenters import event_out, submission_out

router = APIRouter(tags=["events"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: DB) -> list[CategoryOut]:
    counts = dict(db.execute(select(Event.category_id, func.count()).group_by(Event.category_id)).all())
    cats = db.scalars(select(Category).order_by(Category.sort_order, Category.id)).all()
    return [
        CategoryOut(name=c.name, note=c.note, icon_key=c.icon_key, image_url=asset_url(c.image),
                    event_count=counts.get(c.id, 0))
        for c in cats
    ]


@router.get("/events/summary", response_model=SummaryOut)
def events_summary(db: DB) -> SummaryOut:
    return SummaryOut(
        event_count=db.scalar(select(func.count()).select_from(Event)) or 0,
        category_count=db.scalar(select(func.count()).select_from(Category)) or 0,
        geo_levels=GEO_LEVELS,
    )


@router.get("/events", response_model=Page[EventOut])
def list_events(
    db: DB,
    user: OptionalUser,
    pg: Annotated[Pagination, Depends()],
    category: str | None = None,
    featured: Annotated[bool, Query()] = False,
) -> Page[EventOut]:
    stmt = select(Event)
    if featured:
        stmt = stmt.where(Event.featured.is_(True))
    elif category and category != "全部":
        stmt = stmt.join(Category, Category.id == Event.category_id).where(Category.name == category)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Event.sort_order, Event.id)
    if not featured:
        stmt = stmt.offset(pg.offset).limit(pg.page_size)
    events = db.scalars(stmt).unique().all()
    mine = enrolled_event_ids(db, user, [e.id for e in events])
    return Page(items=[event_out(e, e.id in mine) for e in events], total=total)


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: DB, user: OptionalUser) -> EventOut:
    event = get_event_or_404(db, event_id)
    return event_out(event, event.id in enrolled_event_ids(db, user, [event.id]))


@router.post("/events/{event_id}/enroll", response_model=EnrollOut)
def enroll_event(event_id: int, db: DB, user: CurrentUser) -> EnrollOut:
    event = get_event_or_404(db, event_id)
    first, bonus = enroll(db, user, event)
    db.commit()
    db.refresh(event)
    db.refresh(user)
    return EnrollOut(enrolled=True, first_time=first, bonus=bonus, participant_count=event.participant_count,
                     flower_balance=user.flower_balance)


@router.get("/events/{event_id}/submissions", response_model=Page[SubmissionOut])
def event_submissions(event_id: int, db: DB, pg: Annotated[Pagination, Depends()]) -> Page[SubmissionOut]:
    get_event_or_404(db, event_id)
    cond = (Submission.event_id == event_id) & (Submission.status == "approved")
    total = db.scalar(select(func.count()).select_from(Submission).where(cond)) or 0
    subs = db.scalars(
        select(Submission).where(cond)
        .order_by(Submission.flower_count.desc(), Submission.id.asc())
        .offset(pg.offset).limit(pg.page_size)
    ).unique().all()
    return Page(items=[submission_out(s) for s in subs], total=total)
