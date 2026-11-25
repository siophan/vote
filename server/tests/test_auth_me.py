from app.rules import level_info
from tests.conftest import login


def test_health(client):
    assert client.get("/api/v1/health").json() == {"ok": True}


def test_mock_login_creates_user_with_signup_bonus(client):
    r = client.post("/api/v1/auth/login", json={"code": "anything"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    user = body["user"]
    assert user["flower_balance"] == 100
    assert user["growth_value"] == 0
    assert user["level_name"] == "银龄新人"
    assert user["next_level_name"] == "社区新星"
    assert user["next_level_value"] == 300
    assert user["nickname"] == "银龄生活家"
    assert user["city"] == ""  # unset until the user picks one; no fake default city
    assert user["enrolled_count"] == 0 and user["submission_count"] == 0
    assert set(user) == {
        "id", "nickname", "avatar_url", "city", "district", "community", "flower_balance",
        "growth_value", "level_name", "next_level_name", "next_level_value",
        "enrolled_count", "submission_count", "created_at",
    }

    # second login: same user, no second bonus
    again = client.post("/api/v1/auth/login", json={"code": "other"}).json()
    assert again["user"]["id"] == user["id"]
    assert again["user"]["flower_balance"] == 100
    h = {"Authorization": f"Bearer {again['token']}"}
    ledger = client.get("/api/v1/flowers/ledger", headers=h).json()
    assert ledger["total"] == 1
    assert ledger["items"][0]["reason"] == "signup_bonus"
    assert ledger["items"][0]["reason_text"] == "新人礼"


def test_dev_openid_gives_distinct_users(client):
    a = client.post("/api/v1/auth/login", json={"code": "x", "dev_openid": "a"}).json()["user"]
    b = client.post("/api/v1/auth/login", json={"code": "x", "dev_openid": "b"}).json()["user"]
    assert a["id"] != b["id"]


def test_me_requires_auth(client):
    r = client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "请先登录"}
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_me_get_and_patch(client):
    h = login(client)
    me = client.get("/api/v1/me", headers=h).json()
    assert me["flower_balance"] == 100
    r = client.patch("/api/v1/me", json={"nickname": " 桂香阿姨 ", "city": "苏州", "community": "幸福里"}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["nickname"] == "桂香阿姨"
    assert body["city"] == "苏州"
    assert body["community"] == "幸福里"
    assert body["district"] == ""
    # the region picker says 杭州市; free text may say 杭州 — both store 杭州
    assert client.patch("/api/v1/me", json={"city": "杭州市", "district": "西湖区"}, headers=h).json()["city"] == "杭州"
    assert client.patch("/api/v1/me", json={"city": "北京市"}, headers=h).json()["city"] == "北京"
    r = client.patch("/api/v1/me", json={"nickname": "  "}, headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == "昵称不能为空"


def test_avatar_upload(client, tmp_path, monkeypatch):
    import app.routers.me as me_router

    monkeypatch.setattr(me_router, "UPLOADS_DIR", tmp_path)
    h = login(client)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    r = client.post("/api/v1/me/avatar", files={"file": ("a.png", png, "image/png")}, headers=h)
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert url.startswith("http://assets.test/static/uploads/avatars/") and url.endswith(".png")
    assert client.get("/api/v1/me", headers=h).json()["avatar_url"] == url
    bad = client.post("/api/v1/me/avatar", files={"file": ("a.txt", b"hello", "text/plain")}, headers=h)
    assert bad.status_code == 400
    big = client.post("/api/v1/me/avatar", files={"file": ("b.png", png + b"0" * (2 * 1024 * 1024), "image/png")}, headers=h)
    assert big.status_code == 400


def test_levels():
    assert level_info(0) == ("银龄新人", "社区新星", 300)
    assert level_info(299) == ("银龄新人", "社区新星", 300)
    assert level_info(300) == ("社区新星", "银龄新星", 1000)
    assert level_info(1000) == ("银龄新星", "龄花达人", 3000)
    assert level_info(3000) == ("龄花达人", "龄花名家", 8000)
    assert level_info(9000) == ("龄花名家", None, None)


def test_validation_errors_are_400_with_chinese_detail(client):
    r = client.post("/api/v1/auth/login", json=[])
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)
