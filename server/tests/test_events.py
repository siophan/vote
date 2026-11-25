from tests.conftest import login


def test_categories(client):
    cats = client.get("/api/v1/categories").json()
    assert len(cats) == 15
    first = cats[0]
    assert first == {
        "name": "才艺", "note": "唱跳、器乐与舞台表达", "icon_key": "microphone",
        "image_url": "http://assets.test/static/assets/category-talent.webp", "event_count": 6,
    }
    by_name = {c["name"]: c for c in cats}
    assert by_name["红色情怀"]["image_url"].endswith("/red-heart.webp")
    assert by_name["红色情怀"]["event_count"] == 10
    assert sum(c["event_count"] for c in cats) == 110


def test_summary(client):
    assert client.get("/api/v1/events/summary").json() == {"event_count": 110, "category_count": 15, "geo_levels": 6}


def test_featured_events(client):
    r = client.get("/api/v1/events", params={"featured": 1}).json()
    assert r["total"] == 6
    titles = [e["title"] for e in r["items"]]
    assert titles == ["银龄才艺开放麦", "我的银龄活力日", "老手艺新舞台", "我家的家风故事", "我的城市记忆", "同城慢旅行"]


def test_event_list_paging_and_category(client):
    r = client.get("/api/v1/events").json()
    assert r["total"] == 110 and len(r["items"]) == 20
    r = client.get("/api/v1/events", params={"page": 6, "page_size": 20}).json()
    assert len(r["items"]) == 10
    r = client.get("/api/v1/events", params={"page_size": 500}).json()
    assert len(r["items"]) == 100
    r = client.get("/api/v1/events", params={"category": "才艺"}).json()
    assert r["total"] == 6
    assert all(e["category"] == "才艺" for e in r["items"])


def test_event_seed_formulas(client):
    items = client.get("/api/v1/events", params={"page_size": 100}).json()["items"]
    e0 = items[0]
    assert e0 == {
        "id": e0["id"], "title": "银龄才艺开放麦", "category": "才艺",
        "desc": "唱歌、器乐、戏曲与舞蹈都可以，拍下你的舞台时刻。", "geo": "城市→社区组",
        "status_text": "报名进行中", "emoji": "🎤", "icon_key": "microphone",
        "cover_url": "http://assets.test/static/assets/event-cover-01.webp",
        "heat": 94, "participant_count": 818, "flower_count": 1280,
        "reward_text": "舞台麦克风支架 · 420 朵", "ai_allowed": False, "ai_label": "原声/实拍优先",
        "track": "才艺 · 城市 / 社区组", "video_status": "已接入测试 · 待验证", "enrolled": False,
    }
    by_title = {e["title"]: e for e in items}
    # theme scene cover
    assert by_title["戏曲票友会"]["cover_url"].endswith("/theme-scene-01.webp")
    # index 1: ai allowed, video status
    assert by_title["老歌新唱"]["ai_allowed"] is True
    assert by_title["老歌新唱"]["ai_label"] == "AI辅助可选"
    assert by_title["老歌新唱"]["video_status"] == "待提交视频号"
    assert by_title["老歌新唱"]["participant_count"] == 636
    assert by_title["老歌新唱"]["heat"] == 88


def test_event_detail_and_404(client):
    eid = client.get("/api/v1/events").json()["items"][0]["id"]
    assert client.get(f"/api/v1/events/{eid}").json()["title"] == "银龄才艺开放麦"
    r = client.get("/api/v1/events/99999")
    assert r.status_code == 404
    assert r.json() == {"detail": "赛事不存在"}


def test_enroll_idempotent_bonus(client):
    h = login(client)
    before = client.get("/api/v1/events/1").json()["participant_count"]
    r = client.post("/api/v1/events/1/enroll", headers=h).json()
    assert r == {"enrolled": True, "first_time": True, "bonus": 10, "participant_count": before + 1,
                 "flower_balance": 110}
    r = client.post("/api/v1/events/1/enroll", headers=h).json()
    assert r == {"enrolled": True, "first_time": False, "bonus": 0, "participant_count": before + 1,
                 "flower_balance": 110}

    me = client.get("/api/v1/me", headers=h).json()
    assert me["growth_value"] == 10 and me["enrolled_count"] == 1
    assert client.get("/api/v1/events/1", headers=h).json()["enrolled"] is True
    assert client.get("/api/v1/events/1").json()["enrolled"] is False
    enrollments = client.get("/api/v1/me/enrollments", headers=h).json()
    assert [e["id"] for e in enrollments] == [1]
    assert enrollments[0]["enrolled"] is True
    ledger = client.get("/api/v1/flowers/ledger", headers=h).json()
    assert [i["reason"] for i in ledger["items"]] == ["enroll_bonus", "signup_bonus"]
    assert ledger["items"][0]["balance_after"] == 110


def test_enroll_requires_auth_and_existing_event(client):
    assert client.post("/api/v1/events/1/enroll").status_code == 401
    h = login(client)
    assert client.post("/api/v1/events/99999/enroll", headers=h).status_code == 404


def test_enroll_bonus_daily_limit(client, monkeypatch):
    h = login(client)
    before = {i: client.get(f"/api/v1/events/{i}").json()["participant_count"] for i in (1, 2, 3, 4, 5)}
    bonuses = [client.post(f"/api/v1/events/{i}/enroll", headers=h).json()["bonus"] for i in (1, 2, 3, 4)]
    assert bonuses == [10, 10, 10, 0]
    for i in (1, 2, 3, 4):  # every first enrollment still counts as a participant
        assert client.get(f"/api/v1/events/{i}").json()["participant_count"] == before[i] + 1
    me = client.get("/api/v1/me", headers=h).json()
    assert me["flower_balance"] == 130 and me["growth_value"] == 30 and me["enrolled_count"] == 4
    # a new China day resets the allowance
    from datetime import UTC, datetime, timedelta
    import app.services.events as svc
    monkeypatch.setattr(svc, "today_start_utc", lambda: datetime.now(UTC) + timedelta(minutes=1))
    assert client.post("/api/v1/events/5/enroll", headers=h).json()["bonus"] == 10
