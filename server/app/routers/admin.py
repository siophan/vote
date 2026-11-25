from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select

from app.config import get_settings
from app.deps import DB, require_admin
from app.errors import not_found
from app.models import Category, Event, FlowerGift, FlowerLedger, Order, Submission, User
from app.routers.common import Pagination
from app.rules import today_start_utc
from app.schemas import (
    AdjustIn,
    AdminUserOut,
    EventAdminOut,
    EventPatch,
    FeedPatch,
    LedgerPage,
    OrderAdminOut,
    OrderOut,
    Page,
    ReviewIn,
    ShipIn,
    StatsOut,
    SubmissionOut,
)
from app.services.events import get_event_or_404
from app.services.ledger import apply_delta, lock_user
from app.services.orders import ship_order
from app.services.presenters import event_out, ledger_out, order_out, submission_out, user_out
from app.services.submissions import review_submission, update_feed_info

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

SUBMISSION_STATUSES = {"pending", "approved", "rejected"}
ORDER_STATUSES = {"pending_shipment", "shipped", "completed", "cancelled"}
USER_NOT_FOUND = "用户不存在"

PG = Annotated[Pagination, Depends()]


def _page(db: DB, stmt, pg: Pagination, *order_by):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.order_by(*order_by).offset(pg.offset).limit(pg.page_size)).unique().all()
    return rows, total


def _like(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# ---------- overview ----------


@router.get("/stats", response_model=StatsOut)
def admin_stats(db: DB) -> StatsOut:
    since = today_start_utc()

    def count(stmt) -> int:
        return db.scalar(stmt) or 0

    return StatsOut(
        pending_submissions=count(select(func.count()).select_from(Submission).where(Submission.status == "pending")),
        pending_shipments=count(select(func.count()).select_from(Order).where(Order.status == "pending_shipment")),
        users_today=count(select(func.count()).select_from(User).where(User.created_at >= since)),
        flowers_today=count(select(func.coalesce(func.sum(FlowerGift.count), 0)).where(FlowerGift.created_at >= since)),
    )


# ---------- submissions ----------


@router.get("/submissions", response_model=Page[SubmissionOut])
def admin_submissions(db: DB, pg: PG, status: str = "pending", q: str = "") -> Page[SubmissionOut]:
    stmt = select(Submission)
    if status in SUBMISSION_STATUSES:
        stmt = stmt.where(Submission.status == status)
    q = q.strip()
    if q:
        author_ids = select(User.id).where(User.nickname.ilike(_like(q), escape="\\"))
        stmt = stmt.where(or_(Submission.title.ilike(_like(q), escape="\\"), Submission.user_id.in_(author_ids)))
    # pending: oldest first (review queue); otherwise newest first
    order = Submission.id.asc() if status == "pending" else Submission.id.desc()
    subs, total = _page(db, stmt, pg, order)
    return Page(items=[submission_out(s) for s in subs], total=total)


@router.post("/submissions/{submission_id}/review", response_model=SubmissionOut)
def admin_review(submission_id: int, data: ReviewIn, db: DB) -> SubmissionOut:
    return submission_out(review_submission(db, submission_id, data))


@router.patch("/submissions/{submission_id}", response_model=SubmissionOut)
def admin_patch_submission(submission_id: int, data: FeedPatch, db: DB) -> SubmissionOut:
    return submission_out(update_feed_info(db, submission_id, data))


# ---------- orders ----------


def order_admin_out(o: Order) -> OrderAdminOut:
    return OrderAdminOut(**order_out(o).model_dump(), user_id=o.user_id, user_nickname=o.user.nickname)


@router.get("/orders", response_model=Page[OrderAdminOut])
def admin_orders(db: DB, pg: PG, status: str = "pending_shipment") -> Page[OrderAdminOut]:
    stmt = select(Order)
    if status in ORDER_STATUSES:
        stmt = stmt.where(Order.status == status)
    order = Order.id.asc() if status == "pending_shipment" else Order.id.desc()
    orders, total = _page(db, stmt, pg, order)
    return Page(items=[order_admin_out(o) for o in orders], total=total)


@router.post("/orders/{order_id}/ship", response_model=OrderOut)
def admin_ship(order_id: int, db: DB, data: ShipIn | None = None) -> OrderOut:
    return order_out(ship_order(db, order_id, data.tracking_no if data else None))


# ---------- events ----------


def event_admin_out(e: Event) -> EventAdminOut:
    return EventAdminOut(**event_out(e).model_dump(), featured=e.featured, sort_order=e.sort_order)


@router.get("/events", response_model=Page[EventAdminOut])
def admin_events(db: DB, pg: PG, q: str = "", category: str = "", featured: bool = False) -> Page[EventAdminOut]:
    stmt = select(Event)
    q = q.strip()
    if q:
        stmt = stmt.where(Event.title.ilike(_like(q), escape="\\"))
    if category:
        stmt = stmt.join(Category, Category.id == Event.category_id).where(Category.name == category)
    if featured:
        stmt = stmt.where(Event.featured.is_(True))
    events, total = _page(db, stmt, pg, Event.sort_order, Event.id)
    return Page(items=[event_admin_out(e) for e in events], total=total)


@router.patch("/events/{event_id}", response_model=EventAdminOut)
def admin_patch_event(event_id: int, data: EventPatch, db: DB) -> EventAdminOut:
    event = get_event_or_404(db, event_id)
    changes = data.model_dump(exclude_unset=True)
    cover = changes.pop("cover_url", None)
    if cover is not None:
        cover = cover.strip()
        base = get_settings().ASSET_BASE_URL
        event.cover = cover[len(base):] if cover.startswith(base) else cover
    for field, value in changes.items():
        if value is not None:
            setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event_admin_out(event)


# ---------- users & flowers ----------


def user_admin_out(db: DB, u: User) -> AdminUserOut:
    return AdminUserOut(**user_out(db, u).model_dump(), openid=u.openid)


def _user_or_404(db: DB, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise not_found(USER_NOT_FOUND)
    return user


@router.get("/users", response_model=Page[AdminUserOut])
def admin_users(db: DB, pg: PG, q: str = "") -> Page[AdminUserOut]:
    stmt = select(User)
    q = q.strip()
    if q:
        cond = User.nickname.ilike(_like(q), escape="\\")
        if q.isdigit():
            cond = or_(cond, User.id == int(q))
        stmt = stmt.where(cond)
    users, total = _page(db, stmt, pg, User.id.desc())
    return Page(items=[user_admin_out(db, u) for u in users], total=total)


@router.get("/users/{user_id}/ledger", response_model=LedgerPage)
def admin_user_ledger(user_id: int, db: DB, pg: PG) -> LedgerPage:
    user = _user_or_404(db, user_id)
    stmt = select(FlowerLedger).where(FlowerLedger.user_id == user.id)
    entries, total = _page(db, stmt, pg, FlowerLedger.id.desc())
    return LedgerPage(balance=user.flower_balance, items=[ledger_out(e) for e in entries], total=total)


@router.post("/users/{user_id}/flowers", response_model=AdminUserOut)
def admin_adjust_flowers(user_id: int, data: AdjustIn, db: DB) -> AdminUserOut:
    _user_or_404(db, user_id)
    user = lock_user(db, user_id)
    entry = apply_delta(db, user, data.delta, "admin_adjust")
    entry.note = data.note
    db.commit()
    db.refresh(user)
    return user_admin_out(db, user)
