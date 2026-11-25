from sqlalchemy import select

from app.models import FlowerLedger, User
from tests.conftest import approve, balance, login, submit


def _approved_submission(client, author_openid="author", event_id=1, title="作品"):
    h = login(client, author_openid)
    sid = submit(client, h, event_id=event_id, title=title).json()["id"]
    approve(client, sid)
    return h, sid


def test_send_flowers_updates_all_counters(client):
    author, sid = _approved_submission(client)
    fan = login(client, "fan")
    event_before = client.get("/api/v1/events/1").json()["flower_count"]
    author_before = client.get("/api/v1/me", headers=author).json()
    r = client.post(f"/api/v1/submissions/{sid}/flowers", json={"count": 20}, headers=fan)
    assert r.status_code == 200, r.text
    assert r.json() == {"flower_balance": 80, "submission_flower_count": 20}
    assert client.get(f"/api/v1/submissions/{sid}").json()["flower_count"] == 20
    assert client.get("/api/v1/events/1").json()["flower_count"] == event_before + 20
    author_after = client.get("/api/v1/me", headers=author).json()
    assert author_after["flower_balance"] == author_before["flower_balance"] + 20
    assert author_after["growth_value"] == author_before["growth_value"] + 20
    fan_me = client.get("/api/v1/me", headers=fan).json()
    assert fan_me["growth_value"] == 20

    fan_ledger = client.get("/api/v1/flowers/ledger", headers=fan).json()
    assert fan_ledger["balance"] == 80
    assert fan_ledger["items"][0]["delta"] == -20
    assert fan_ledger["items"][0]["reason_text"] == "送出小红花"
    assert fan_ledger["items"][0]["balance_after"] == 80
    author_ledger = client.get("/api/v1/flowers/ledger", headers=author).json()
    assert author_ledger["items"][0]["reason"] == "receive_flower"
    assert author_ledger["items"][0]["delta"] == 20


def test_cannot_send_to_own_work(client):
    author, sid = _approved_submission(client)
    r = client.post(f"/api/v1/submissions/{sid}/flowers", json={"count": 1}, headers=author)
    assert r.status_code == 400
    assert r.json()["detail"] == "不能给自己的作品送花"


def test_insufficient_balance(client):
    sids = [_approved_submission(client, f"author{i}")[1] for i in range(6)]
    fan = login(client, "fan")
    for sid in sids[:4]:  # 4 × 20 (the per-author daily cap) + 19 → 1 left
        assert client.post(f"/api/v1/submissions/{sid}/flowers", json={"count": 20}, headers=fan).status_code == 200
    assert client.post(f"/api/v1/submissions/{sids[4]}/flowers", json={"count": 19}, headers=fan).status_code == 200
    r = client.post(f"/api/v1/submissions/{sids[5]}/flowers", json={"count": 2}, headers=fan)
    assert r.status_code == 400
    assert r.json()["detail"] == "小红花余额不足"
    assert balance(client, fan) == 1
    assert client.get(f"/api/v1/submissions/{sids[5]}").json()["flower_count"] == 0


def test_count_bounds_and_pending(client):
    h = login(client, "author")
    pending_sid = submit(client, h).json()["id"]
    fan = login(client, "fan")
    assert client.post(f"/api/v1/submissions/{pending_sid}/flowers", json={"count": 1}, headers=fan).status_code == 404
    approve(client, pending_sid)
    for bad in (0, -5, 100):
        r = client.post(f"/api/v1/submissions/{pending_sid}/flowers", json={"count": bad}, headers=fan)
        assert r.status_code == 400
        assert r.json()["detail"] == "每次可送 1–99 朵小红花"
    assert client.post("/api/v1/submissions/9999/flowers", json={"count": 1}, headers=fan).status_code == 404
    assert client.post(f"/api/v1/submissions/{pending_sid}/flowers", json={"count": 1}).status_code == 401


def test_ledger_consistency_and_paging(client, db):
    _, sid = _approved_submission(client)
    fan = login(client, "fan")
    for _ in range(5):
        client.post(f"/api/v1/submissions/{sid}/flowers", json={"count": 3}, headers=fan)
    page1 = client.get("/api/v1/flowers/ledger", params={"page": 1, "page_size": 4}, headers=fan).json()
    page2 = client.get("/api/v1/flowers/ledger", params={"page": 2, "page_size": 4}, headers=fan).json()
    assert page1["total"] == 6 and len(page1["items"]) == 4 and len(page2["items"]) == 2
    assert page1["items"][0]["id"] > page1["items"][-1]["id"]
    # every user's balance equals the sum of their ledger and the latest balance_after
    for user in db.scalars(select(User)):
        rows = db.scalars(select(FlowerLedger).where(FlowerLedger.user_id == user.id).order_by(FlowerLedger.id)).all()
        assert sum(r.delta for r in rows) == user.flower_balance
        assert rows[-1].balance_after == user.flower_balance
    assert client.get("/api/v1/flowers/ledger").status_code == 401


def test_rankings(client):
    a_h, s1 = _approved_submission(client, "a", title="甲")
    b_h, s2 = _approved_submission(client, "b", event_id=2, title="乙")
    client.patch("/api/v1/me", json={"city": "苏州"}, headers=b_h)
    pending = submit(client, a_h, title="未审核").json()["id"]
    fan = login(client, "fan")
    client.post(f"/api/v1/submissions/{s2}/flowers", json={"count": 9}, headers=fan)
    client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 4}, headers=fan)

    rows = client.get("/api/v1/rankings").json()
    assert [r["submission_id"] for r in rows] == [s2, s1]
    assert pending not in [r["submission_id"] for r in rows]
    assert rows[0] == {
        "rank": 1, "submission_id": s2, "author_id": rows[0]["author_id"], "title": "乙", "event_title": "老歌新唱",
        "author_nickname": "银龄生活家", "author_avatar_url": None, "city": "苏州", "flower_count": 9,
    }
    assert rows[1]["rank"] == 2
    client.patch("/api/v1/me", json={"city": "杭州市"}, headers=a_h)  # stored as 杭州
    assert [r["submission_id"] for r in client.get("/api/v1/rankings", params={"city": "杭州"}).json()] == [s1]
    assert [r["submission_id"] for r in client.get("/api/v1/rankings", params={"city": "杭州市"}).json()] == [s1]
    assert rows[0]["author_id"] != rows[1]["author_id"]
    assert client.get("/api/v1/rankings", params={"category": "健康"}).json() == []
    assert len(client.get("/api/v1/rankings", params={"limit": 1}).json()) == 1


def test_daily_gift_cap_per_author(client, monkeypatch):
    _, s1 = _approved_submission(client, "a")
    _, s2 = _approved_submission(client, "b", event_id=2)
    fan = login(client, "fan")
    assert client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 15}, headers=fan).status_code == 200
    r = client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 6}, headers=fan)
    assert r.status_code == 400 and r.json()["detail"] == "每天给同一位作者最多送 20 朵，今天还能送 5 朵"
    assert client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 5}, headers=fan).status_code == 200
    r = client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 1}, headers=fan)
    assert r.status_code == 400 and r.json()["detail"] == "今天已给这位作者送了 20 朵，明天再来支持吧"
    # another author has a separate allowance
    assert client.post(f"/api/v1/submissions/{s2}/flowers", json={"count": 20}, headers=fan).status_code == 200
    assert balance(client, fan) == 60
    # the next day the allowance resets
    from datetime import UTC, datetime, timedelta
    import app.services.submissions as svc
    monkeypatch.setattr(svc, "today_start_utc", lambda: datetime.now(UTC) + timedelta(minutes=1))
    assert client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 20}, headers=fan).status_code == 200
