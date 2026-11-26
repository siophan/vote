import pytest

from app.rules import DUPLICATE_VIDEO_OTHER, DUPLICATE_VIDEO_OWN, VIDEO_LINK_ERROR, normalize_city, normalize_video_url
from tests.conftest import ADMIN, GOOD_LINK, approve, balance, login, submit


@pytest.mark.parametrize("url", [
    "https://weixin.qq.com/sph/AbCdEf123",
    "https://channels.weixin.qq.com/web/pages/feed?eid=abc",
    "https://finder.video.qq.com/251/20302/stodownload?x=1",
    "  https://weixin.qq.com/sph/xyz  ",
    "张阿姨的视频号作品 https://weixin.qq.com/sph/AbC123 快来看",
])
def test_link_accept(url):
    assert normalize_video_url(url) is not None


@pytest.mark.parametrize("url", [
    "http://weixin.qq.com/sph/AbCdEf123",
    "https://www.douyin.com/video/123",
    "https://weixin.qq.com.evil.com/sph/x",
    "https://evilweixin.qq.com/sph/x",
    "https://user:pw@weixin.qq.com/sph/x",
    "https://weixin.qq.com:8443/sph/x",
    "ftp://weixin.qq.com/sph/x",
    "weixin.qq.com/sph/x",
    "garbage",
    "",
    "https://",
    "看 https://weixin.qq.com/sph/a 和 https://weixin.qq.com/sph/b",
])
def test_link_reject(url):
    assert normalize_video_url(url) is None


def test_submit_rejects_bad_links(client):
    h = login(client)
    for url in ["http://weixin.qq.com/sph/x", "https://v.douyin.com/abc", "not a link at all"]:
        r = submit(client, h, url=url)
        assert r.status_code == 400
        assert r.json() == {"detail": VIDEO_LINK_ERROR}
    # nothing was created, and no auto-enrollment happened
    me = client.get("/api/v1/me", headers=h).json()
    assert me["submission_count"] == 0 and me["enrolled_count"] == 0


def test_submit_auto_enrolls_and_is_pending(client):
    h = login(client)
    r = submit(client, h, url="https://channels.weixin.qq.com/web/pages/feed?eid=1")
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["status"] == "pending"
    assert sub["event_id"] == 1 and sub["event_title"] == "银龄才艺开放麦"
    assert sub["flower_count"] == 0 and sub["reject_reason"] is None
    assert sub["description"] == ""
    assert sub["author"]["nickname"] == "银龄生活家"
    assert set(sub) == {
        "id", "event_id", "event_title", "title", "description", "video_url", "finder_user_name",
        "feed_id", "feed_token", "status", "reject_reason", "flower_count", "author", "created_at",
    }
    me = client.get("/api/v1/me", headers=h).json()
    assert me["enrolled_count"] == 1 and me["submission_count"] == 1
    assert me["flower_balance"] == 110  # signup + enroll bonus
    # enrolling explicitly afterwards is not a first time
    assert client.post("/api/v1/events/1/enroll", headers=h).json()["first_time"] is False
    # second submission to same event: no extra enroll bonus
    submit(client, h, title="第二条")
    assert balance(client, h) == 110


def test_submit_validation(client):
    h = login(client)
    assert submit(client, h, event_id=99999).status_code == 404
    r = submit(client, h, title="   ")
    assert r.status_code == 400
    assert client.post("/api/v1/submissions", json={"event_id": 1, "title": "x", "video_url": GOOD_LINK}).status_code == 401


def test_pending_visibility(client):
    author = login(client, "author")
    other = login(client, "other")
    sid = submit(client, author).json()["id"]
    assert client.get(f"/api/v1/submissions/{sid}", headers=author).status_code == 200
    assert client.get(f"/api/v1/submissions/{sid}", headers=other).status_code == 404
    assert client.get(f"/api/v1/submissions/{sid}").status_code == 404
    assert client.get("/api/v1/events/1/submissions").json() == {"items": [], "total": 0}
    mine = client.get("/api/v1/me/submissions", headers=author).json()
    assert [s["id"] for s in mine] == [sid]
    approve(client, sid)
    assert client.get(f"/api/v1/submissions/{sid}").json()["status"] == "approved"
    listing = client.get("/api/v1/events/1/submissions").json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == sid


def test_admin_approve_grants_bonus_once(client):
    h = login(client)
    sid = submit(client, h).json()["id"]
    assert balance(client, h) == 110
    body = approve(client, sid, finder_user_name="sphABC", feed_id="export/xyz", feed_token="tok")
    assert body["status"] == "approved"
    assert body["finder_user_name"] == "sphABC" and body["feed_id"] == "export/xyz" and body["feed_token"] == "token/tok"
    assert balance(client, h) == 160
    approve(client, sid)  # re-approve: no second bonus
    assert balance(client, h) == 160
    me = client.get("/api/v1/me", headers=h).json()
    assert me["growth_value"] == 60
    reasons = [i["reason"] for i in client.get("/api/v1/flowers/ledger", headers=h).json()["items"]]
    assert reasons.count("submission_approved") == 1


def test_admin_reject(client):
    h = login(client)
    sid = submit(client, h).json()["id"]
    r = client.post(f"/api/v1/admin/submissions/{sid}/review", json={"action": "reject", "reason": "链接打不开"}, headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected" and r.json()["reject_reason"] == "链接打不开"
    assert balance(client, h) == 110
    assert client.get(f"/api/v1/submissions/{sid}", headers=h).json()["status"] == "rejected"
    # rejected work cannot receive flowers
    other = login(client, "other")
    assert client.post(f"/api/v1/submissions/{sid}/flowers", json={"count": 1}, headers=other).status_code == 404


def test_admin_list_and_review_404(client):
    h = login(client)
    s1 = submit(client, h).json()["id"]
    s2 = submit(client, h, title="二").json()["id"]
    approve(client, s1)
    pending = client.get("/api/v1/admin/submissions", headers=ADMIN).json()
    assert [s["id"] for s in pending["items"]] == [s2] and pending["total"] == 1
    approved = client.get("/api/v1/admin/submissions", params={"status": "approved"}, headers=ADMIN).json()
    assert [s["id"] for s in approved["items"]] == [s1]
    everything = client.get("/api/v1/admin/submissions", params={"status": "all"}, headers=ADMIN).json()
    assert everything["total"] == 2
    r = client.post("/api/v1/admin/submissions/9999/review", json={"action": "approve"}, headers=ADMIN)
    assert r.status_code == 404
    r = client.post(f"/api/v1/admin/submissions/{s2}/review", json={"action": "maybe"}, headers=ADMIN)
    assert r.status_code == 400


def test_admin_token_required(client):
    for headers in ({}, {"X-Admin-Token": "wrong"}):
        assert client.get("/api/v1/admin/submissions", headers=headers).status_code == 403
        assert client.post("/api/v1/admin/submissions/1/review", json={"action": "approve"}, headers=headers).status_code == 403
        assert client.post("/api/v1/admin/orders/1/ship", json={}, headers=headers).status_code == 403
        assert client.patch("/api/v1/admin/events/1", json={"heat": 1}, headers=headers).status_code == 403
    # a user JWT is not an admin token
    h = login(client)
    assert client.get("/api/v1/admin/submissions", headers=h).status_code == 403


def test_admin_event_patch(client):
    r = client.patch(
        "/api/v1/admin/events/1",
        json={"heat": 99, "participant_count": 1000, "reward_text": "新奖励", "ai_allowed": True,
              "ai_label": "AI辅助可选", "video_status": "支持视频号链接", "cover_url": "theme-scene-05.webp"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    e = r.json()
    assert e["heat"] == 99 and e["participant_count"] == 1000 and e["reward_text"] == "新奖励"
    assert e["ai_allowed"] is True and e["video_status"] == "支持视频号链接"
    assert e["cover_url"] == "http://assets.test/static/assets/theme-scene-05.webp"
    assert e["track"] == "才艺 · 城市 / 社区组"  # untouched
    r = client.patch("/api/v1/admin/events/1", json={"cover_url": "https://cdn.example.com/a.webp"}, headers=ADMIN)
    assert r.json()["cover_url"] == "https://cdn.example.com/a.webp"
    r = client.patch("/api/v1/admin/events/1", json={"cover_url": "http://assets.test/static/assets/event-cover-09.webp"}, headers=ADMIN)
    assert r.json()["cover_url"] == "http://assets.test/static/assets/event-cover-09.webp"
    assert client.get("/api/v1/events/1").json()["heat"] == 99
    assert client.patch("/api/v1/admin/events/99999", json={"heat": 1}, headers=ADMIN).status_code == 404


def test_same_video_only_one_live_submission(client):
    link = GOOD_LINK + "dup"
    a = login(client, "a")
    first = submit(client, a, event_id=1, url=link)
    assert first.status_code == 200
    # same user, another event: farming APPROVAL_BONUS again is blocked
    r = submit(client, a, event_id=2, url=link)
    assert r.status_code == 400 and r.json()["detail"] == DUPLICATE_VIDEO_OWN
    # another user cannot enter someone else's video either
    r = submit(client, login(client, "b"), event_id=3, url=link)
    assert r.status_code == 400 and r.json()["detail"] == DUPLICATE_VIDEO_OTHER
    # once approved it is still taken
    approve(client, first.json()["id"])
    assert submit(client, a, event_id=2, url=link).status_code == 400
    assert balance(client, a) == 100 + 10 + 50


def test_rejected_video_can_be_resubmitted(client):
    link = GOOD_LINK + "again"
    h = login(client)
    sid = submit(client, h, event_id=1, url=link).json()["id"]
    client.post(f"/api/v1/admin/submissions/{sid}/review", json={"action": "reject", "reason": "选错赛事"}, headers=ADMIN)
    again = submit(client, h, event_id=2, url=link)
    assert again.status_code == 200
    # the old rejected one cannot be re-approved while the new one is live
    r = client.post(f"/api/v1/admin/submissions/{sid}/review", json={"action": "approve", "feed_token": "t"},
                    headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"] == DUPLICATE_VIDEO_OWN
    approve(client, again.json()["id"])


@pytest.mark.parametrize("raw,city", [("杭州市", "杭州"), (" 杭州 ", "杭州"), ("北京市", "北京"), ("", ""), (None, ""),
                                      ("恩施土家族苗族自治州", "恩施土家族苗族自治州")])
def test_normalize_city(raw, city):
    assert normalize_city(raw) == city


@pytest.mark.parametrize("raw,canonical", [
    ("https://weixin.qq.com/sph/AbC123", "https://weixin.qq.com/sph/AbC123"),
    ("HTTPS://WEIXIN.QQ.COM/sph/AbC123/", "https://weixin.qq.com/sph/AbC123"),
    ("https://weixin.qq.com:443/sph/AbC123#share", "https://weixin.qq.com/sph/AbC123"),
    ("https://channels.weixin.qq.com/web/pages/feed?eid=abc", "https://channels.weixin.qq.com/web/pages/feed?eid=abc"),
])
def test_link_canonical_form(raw, canonical):
    assert normalize_video_url(raw) == canonical


def test_trivially_different_copies_are_duplicates(client):
    h = login(client)
    assert submit(client, h, event_id=1, url=GOOD_LINK + "Case").status_code == 200
    r = submit(client, h, event_id=2, url=GOOD_LINK.upper().replace("/SPH/", "/sph/").replace("ABCDEF123", "AbCdEf123") + "Case/#x")
    assert r.status_code == 400 and r.json()["detail"] == DUPLICATE_VIDEO_OWN


def test_same_feed_with_different_links_blocked_at_review(client):
    a, b = login(client, "a"), login(client, "b")
    s1 = submit(client, a, event_id=1).json()["id"]
    s2 = submit(client, b, event_id=2).json()["id"]  # another short link, same video
    approve(client, s1, finder_user_name="sphAuthor", feed_id="export/xyz")
    r = client.post(f"/api/v1/admin/submissions/{s2}/review",
                    json={"action": "approve", "finder_user_name": "sphAuthor", "feed_id": "export/xyz",
                          "feed_token": "tok-s2"}, headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"] == f"这条视频与作品 #{s1} 是同一条视频，请驳回本条投稿"
    assert client.get(f"/api/v1/submissions/{s2}", headers=b).json()["status"] == "pending"
    assert balance(client, b) == 110  # no approval bonus
    # same check for feed_token
    s3 = submit(client, b, event_id=3).json()["id"]
    approve(client, s1, feed_token="tok-1", finder_user_name="sphAuthor", feed_id="export/xyz")
    r = client.post(f"/api/v1/admin/submissions/{s3}/review",
                    json={"action": "approve", "feed_token": "tok-1", "finder_user_name": "sphOther", "feed_id": "export/o"},
                    headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"] == f"这条视频与作品 #{s1} 是同一条视频，请驳回本条投稿"
    # once the first is rejected the feed is free again
    client.post(f"/api/v1/admin/submissions/{s1}/review", json={"action": "reject", "reason": "x"}, headers=ADMIN)
    approve(client, s2, finder_user_name="sphAuthor", feed_id="export/xyz")
