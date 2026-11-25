import os

os.environ.update(
    DATABASE_URL="sqlite://",
    WECHAT_MOCK_LOGIN="true",
    ADMIN_TOKEN="test-admin",
    JWT_SECRET="test-secret-0123456789abcdef0123456789abcdef",
    ASSET_BASE_URL="http://assets.test/static/assets/",
    UPLOAD_BASE_URL="http://assets.test/static/uploads/",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

ADMIN = {"X-Admin-Token": "test-admin"}
GOOD_LINK = "https://weixin.qq.com/sph/AbCdEf123"


# Default: in-memory SQLite. Set TEST_DATABASE_URL (a throwaway Postgres DB!)
# to run the same suite against PostgreSQL; its tables are dropped per test.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture()
def session_factory():
    if TEST_DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(engine, "connect")
        def _fk(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    else:
        engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        seed(db)
    yield factory
    engine.dispose()


@pytest.fixture()
def db(session_factory):
    with session_factory() as s:
        yield s


@pytest.fixture()
def client(session_factory):
    def _get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, openid: str = "user_a") -> dict:
    r = client.post("/api/v1/auth/login", json={"code": "x", "dev_openid": openid})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


_link_seq = iter(range(1, 1_000_000))


def submit(client, headers, event_id: int = 1, url: str | None = None, title: str = "我的作品"):
    """A fresh video link per call unless `url` is given: one video can back
    only one live submission."""
    if url is None:
        url = f"{GOOD_LINK}{next(_link_seq)}"
    return client.post(
        "/api/v1/submissions",
        json={"event_id": event_id, "title": title, "video_url": url},
        headers=headers,
    )


FEED_KEYS = ("feed_token", "finder_user_name", "feed_id")


def approve(client, submission_id: int, **extra):
    """Approving requires 视频号 info; default to a token unique to the submission."""
    if not any(k in extra for k in FEED_KEYS):
        extra["feed_token"] = f"tok-auto-{submission_id}"
    r = client.post(
        f"/api/v1/admin/submissions/{submission_id}/review",
        json={"action": "approve", **extra},
        headers=ADMIN,
    )
    assert r.status_code == 200, r.text
    return r.json()


def balance(client, headers) -> int:
    return client.get("/api/v1/me", headers=headers).json()["flower_balance"]
