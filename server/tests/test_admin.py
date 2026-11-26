import pytest

from tests.conftest import ADMIN, approve, balance, login, submit

FEED_INFO_REQUIRED = "请填写视频 token"


def _review(client, sid, **body):
    return client.post(f"/api/v1/admin/submissions/{sid}/review", json={"action": "approve", **body}, headers=ADMIN)


# ---------- review requires 视频号 info ----------

def test_approve_requires_feed_info(client):
    h = login(client)
    sid = submit(client, h).json()["id"]
    r = _review(client, sid)
    assert r.status_code == 400 and r.json()["detail"] == FEED_INFO_REQUIRED
    r = _review(client, sid, feed_token="   ")
    assert r.status_code == 400 and r.json()["detail"] == FEED_INFO_REQUIRED
    assert client.get(f"/api/v1/submissions/{sid}", headers=h).json()["status"] == "pending"
    assert balance(client, h) == 110
    # reject needs no token
    r = client.post(f"/api/v1/admin/submissions/{sid}/review", json={"action": "reject", "reason": "x"}, headers=ADMIN)
    assert r.status_code == 200


def test_approve_requires_token_not_finder(client):
    sid = submit(client, login(client)).json()["id"]
    r = _review(client, sid, finder_user_name="sphAuthor", feed_id="export/1")
    assert r.status_code == 400 and r.json()["detail"] == FEED_INFO_REQUIRED
    r = _review(client, sid, feed_token="tok-only")
    assert r.status_code == 200
    body = r.json()
    # the refused review saved nothing; token alone is enough
    assert body["feed_token"] == "token/tok-only" and body["finder_user_name"] is None and body["feed_id"] is None


@pytest.mark.parametrize("optional", [{}, {"finder_user_name": "sph"}, {"feed_id": "e/1"}])
def test_finder_fields_are_optional(client, optional):
    sid = submit(client, login(client)).json()["id"]
    assert _review(client, sid, feed_token=f"tok-{len(optional)}", **optional).status_code == 200


def test_approve_uses_stored_feed_info(client):
    sid = submit(client, login(client)).json()["id"]
    assert client.patch(f"/api/v1/admin/submissions/{sid}", json={"feed_token": "tok-stored"},
                        headers=ADMIN).status_code == 200
    r = _review(client, sid)
    assert r.status_code == 200 and r.json()["feed_token"] == "token/tok-stored"


def test_patch_feed_info(client):
    a, b = login(client, "a"), login(client, "b")
    s1 = submit(client, a).json()["id"]
    s2 = submit(client, b, event_id=2).json()["id"]
    approve(client, s1, feed_token="tok-1")
    r = client.patch(f"/api/v1/admin/submissions/{s2}", json={"finder_user_name": "sph", "feed_id": "e/1"}, headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["finder_user_name"] == "sph" and body["feed_id"] == "e/1" and body["status"] == "pending"
    # same video as another live submission
    r = client.patch(f"/api/v1/admin/submissions/{s2}", json={"feed_token": "tok-1"}, headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"] == f"这条视频与作品 #{s1} 是同一条视频，请驳回本条投稿"
    assert client.patch("/api/v1/admin/submissions/9999", json={"feed_token": "x"}, headers=ADMIN).status_code == 404


def test_patch_cannot_clear_approved(client):
    sid = submit(client, login(client)).json()["id"]
    approve(client, sid, feed_token="tok-x")
    r = client.patch(f"/api/v1/admin/submissions/{sid}", json={"feed_token": ""}, headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"] == FEED_INFO_REQUIRED
    # the optional 视频号 ID / feed_id can be added and cleared
    r = client.patch(f"/api/v1/admin/submissions/{sid}", json={"finder_user_name": "sph", "feed_id": "e/2"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["feed_id"] == "e/2"
    r = client.patch(f"/api/v1/admin/submissions/{sid}",
                     json={"feed_token": "tok-y", "finder_user_name": "", "feed_id": ""}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["feed_token"] == "token/tok-y" and r.json()["feed_id"] is None


# ---------- lists & stats ----------

def test_admin_lists_paginated(client):
    a, b = login(client, "a"), login(client, "b")
    client.patch("/api/v1/me", json={"nickname": "桂香阿姨"}, headers=a)
    for i in range(3):
        submit(client, a, event_id=i + 1, title=f"二胡{i}")
    submit(client, b, title="太极")
    page = client.get("/api/v1/admin/submissions", params={"page": 1, "page_size": 2}, headers=ADMIN).json()
    assert page["total"] == 4 and len(page["items"]) == 2
    page2 = client.get("/api/v1/admin/submissions", params={"page": 2, "page_size": 2}, headers=ADMIN).json()
    assert {s["id"] for s in page["items"]}.isdisjoint(s["id"] for s in page2["items"])
    by_title = client.get("/api/v1/admin/submissions", params={"q": "太极"}, headers=ADMIN).json()
    assert [s["title"] for s in by_title["items"]] == ["太极"]
    by_author = client.get("/api/v1/admin/submissions", params={"q": "桂香"}, headers=ADMIN).json()
    assert by_author["total"] == 3
    assert client.get("/api/v1/admin/orders", headers=ADMIN).json() == {"items": [], "total": 0}


def test_stats(client):
    a, b = login(client, "a"), login(client, "b")
    s1 = submit(client, a).json()["id"]
    submit(client, a, event_id=2)
    approve(client, s1)
    client.post(f"/api/v1/submissions/{s1}/flowers", json={"count": 3}, headers=b)
    stats = client.get("/api/v1/admin/stats", headers=ADMIN).json()
    assert stats == {"pending_submissions": 1, "pending_shipments": 0, "users_today": 2, "flowers_today": 3}
    assert client.get("/api/v1/admin/stats").status_code == 403


# ---------- events ----------

def test_admin_events(client):
    page = client.get("/api/v1/admin/events", params={"page_size": 5}, headers=ADMIN).json()
    assert page["total"] == 110 and len(page["items"]) == 5
    first = page["items"][0]
    assert "featured" in first and "sort_order" in first
    found = client.get("/api/v1/admin/events", params={"q": "开放麦"}, headers=ADMIN).json()
    assert any(e["title"] == "银龄才艺开放麦" for e in found["items"])
    eid = found["items"][0]["id"]
    featured_before = len(client.get("/api/v1/events?featured=1").json()["items"])
    r = client.patch(f"/api/v1/admin/events/{eid}", json={"featured": not found["items"][0]["featured"]}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["featured"] is (not found["items"][0]["featured"])
    featured_after = len(client.get("/api/v1/events?featured=1").json()["items"])
    assert abs(featured_after - featured_before) == 1


# ---------- users & flowers ----------

def test_admin_users_search(client):
    a = login(client, "a")
    login(client, "b")
    client.patch("/api/v1/me", json={"nickname": "桂香阿姨", "city": "杭州"}, headers=a)
    uid = client.get("/api/v1/me", headers=a).json()["id"]
    page = client.get("/api/v1/admin/users", headers=ADMIN).json()
    assert page["total"] == 2
    assert page["items"][0]["id"] > page["items"][1]["id"]  # newest first
    by_name = client.get("/api/v1/admin/users", params={"q": "桂香"}, headers=ADMIN).json()
    assert [u["id"] for u in by_name["items"]] == [uid]
    assert by_name["items"][0]["openid"] == "a" and by_name["items"][0]["flower_balance"] == 100
    by_id = client.get("/api/v1/admin/users", params={"q": str(uid)}, headers=ADMIN).json()
    assert [u["id"] for u in by_id["items"]] == [uid]


def test_admin_adjust_flowers(client):
    h = login(client)
    uid = client.get("/api/v1/me", headers=h).json()["id"]
    r = client.post(f"/api/v1/admin/users/{uid}/flowers", json={"delta": 30, "note": "线下活动补发"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["flower_balance"] == 130
    growth = client.get("/api/v1/me", headers=h).json()["growth_value"]
    r = client.post(f"/api/v1/admin/users/{uid}/flowers", json={"delta": -20, "note": "误发扣回"}, headers=ADMIN)
    assert r.json()["flower_balance"] == 110
    assert client.get("/api/v1/me", headers=h).json()["growth_value"] == growth  # no growth change
    ledger = client.get(f"/api/v1/admin/users/{uid}/ledger", headers=ADMIN).json()
    top = ledger["items"][0]
    assert top["reason"] == "admin_adjust" and top["delta"] == -20 and top["note"] == "误发扣回"
    assert top["reason_text"] == "运营调整" and ledger["balance"] == 110 and ledger["total"] == 3
    # the user sees it in their own ledger too
    mine = client.get("/api/v1/flowers/ledger", headers=h).json()["items"][0]
    assert mine["note"] == "误发扣回"
    assert client.post("/api/v1/admin/users/9999/flowers", json={"delta": 1, "note": "x"}, headers=ADMIN).status_code == 404


def test_admin_adjust_negative_balance(client):
    h = login(client)
    uid = client.get("/api/v1/me", headers=h).json()["id"]
    r = client.post(f"/api/v1/admin/users/{uid}/flowers", json={"delta": -101, "note": "扣"}, headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"] == "小红花余额不足"
    assert balance(client, h) == 100
    assert client.get(f"/api/v1/admin/users/{uid}/ledger", headers=ADMIN).json()["total"] == 1


def test_admin_adjust_requires_note(client):
    h = login(client)
    uid = client.get("/api/v1/me", headers=h).json()["id"]
    for body in ({"delta": 5}, {"delta": 5, "note": "   "}, {"delta": 0, "note": "x"}, {"delta": 100001, "note": "x"}):
        assert client.post(f"/api/v1/admin/users/{uid}/flowers", json=body, headers=ADMIN).status_code == 400, body
    assert balance(client, h) == 100


@pytest.mark.parametrize("raw,stored", [("ApYGPPNRF", "token/ApYGPPNRF"), (" token/ApYGPPNRF ", "token/ApYGPPNRF")])
def test_feed_token_stored_with_prefix(client, raw, stored):
    sid = submit(client, login(client)).json()["id"]
    r = _review(client, sid, feed_token=raw)
    assert r.status_code == 200 and r.json()["feed_token"] == stored


def test_bare_and_prefixed_token_are_same_video(client):
    a, b = login(client, "a"), login(client, "b")
    s1 = submit(client, a).json()["id"]
    s2 = submit(client, b, event_id=2).json()["id"]
    approve(client, s1, feed_token="ApYGPPNRF")
    r = _review(client, s2, feed_token="token/ApYGPPNRF")
    assert r.status_code == 400 and r.json()["detail"] == f"这条视频与作品 #{s1} 是同一条视频，请驳回本条投稿"
