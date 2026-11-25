import uuid

from fastapi import APIRouter, UploadFile
from sqlalchemy import select

from app.config import UPLOADS_DIR
from app.deps import DB, CurrentUser
from app.errors import bad_request
from app.models import Enrollment, Event, Order, Submission
from app.rules import normalize_city, upload_url
from app.schemas import AvatarOut, EventOut, MePatch, OrderOut, SubmissionOut, UserOut
from app.services.presenters import event_out, order_out, submission_out, user_out

router = APIRouter(prefix="/me", tags=["me"])

MAX_AVATAR_BYTES = 2 * 1024 * 1024


@router.get("", response_model=UserOut)
def get_me(user: CurrentUser, db: DB) -> UserOut:
    return user_out(db, user)


@router.patch("", response_model=UserOut)
def patch_me(data: MePatch, user: CurrentUser, db: DB) -> UserOut:
    changes = data.model_dump(exclude_unset=True)
    if "nickname" in changes:
        nickname = (changes["nickname"] or "").strip()
        if not nickname:
            raise bad_request("昵称不能为空")
        user.nickname = nickname
    if "avatar_url" in changes:
        user.avatar_url = (changes["avatar_url"] or "").strip() or None
    if changes.get("city") is not None:
        user.city = normalize_city(changes["city"])
    for field in ("district", "community"):
        if field in changes and changes[field] is not None:
            setattr(user, field, changes[field].strip())
    db.commit()
    db.refresh(user)
    return user_out(db, user)


def _image_ext(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


@router.post("/avatar", response_model=AvatarOut)
def upload_avatar(file: UploadFile, user: CurrentUser, db: DB) -> AvatarOut:
    content = file.file.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise bad_request("头像图片不能超过 2MB")
    ext = _image_ext(content[:16])
    if not content or ext is None:
        raise bad_request("请上传 JPG / PNG / WEBP / GIF 图片")
    rel = f"avatars/{user.id}-{uuid.uuid4().hex}.{ext}"
    dest = UPLOADS_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    url = upload_url(rel)
    user.avatar_url = url
    db.commit()
    return AvatarOut(avatar_url=url)


@router.get("/enrollments", response_model=list[EventOut])
def my_enrollments(user: CurrentUser, db: DB) -> list[EventOut]:
    events = db.scalars(
        select(Event).join(Enrollment, Enrollment.event_id == Event.id)
        .where(Enrollment.user_id == user.id)
        .order_by(Enrollment.created_at.desc(), Enrollment.id.desc())
    ).unique().all()
    return [event_out(e, enrolled=True) for e in events]


@router.get("/submissions", response_model=list[SubmissionOut])
def my_submissions(user: CurrentUser, db: DB) -> list[SubmissionOut]:
    subs = db.scalars(
        select(Submission).where(Submission.user_id == user.id).order_by(Submission.id.desc())
    ).unique().all()
    return [submission_out(s) for s in subs]


@router.get("/orders", response_model=list[OrderOut])
def my_orders(user: CurrentUser, db: DB) -> list[OrderOut]:
    orders = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).unique().all()
    return [order_out(o) for o in orders]
