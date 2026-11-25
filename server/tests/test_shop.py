from tests.conftest import ADMIN, approve, balance, login, submit

ADDRESS = {"name": "王阿姨", "phone": "13800000000", "province": "浙江省", "city": "杭州市",
           "district": "西湖区", "detail": "文三路 1 号"}


def _product(client, name):
    return next(p for p in client.get("/api/v1/products").json() if p["name"] == name)


def _rich_user(client, db, openid="buyer", amount=5000):
    from app.models import User
    from app.services.ledger import apply_delta, lock_user

    h = login(client, openid)
    uid = client.get("/api/v1/me", headers=h).json()["id"]
    apply_delta(db, lock_user(db, uid), amount, "admin_adjust")
    db.commit()
    assert db.get(User, uid).flower_balance == 100 + amount
    return h


def test_products(client):
    products = client.get("/api/v1/products").json()
    assert [p["name"] for p in products] == ["艾草暖腰带", "轻食食养礼盒", "手作工具包", "银龄出行包", "社区公益包"]
    belt = products[0]
    assert belt == {
        "id": belt["id"], "name": "艾草暖腰带", "subtitle": "适合日常保暖与送长辈",
        "reward_desc": "健康打卡、太极和健步走赛季奖励", "category": "暖心日用", "kind": "goods",
        "price": 680, "image_url": "http://assets.test/static/assets/reward-warm-belt.webp",
        "stock": 999, "featured": True,
    }
    featured = client.get("/api/v1/products", params={"featured": 1}).json()
    assert len(featured) == 4 and all(p["featured"] for p in featured)
    assert [p["name"] for p in client.get("/api/v1/products", params={"category": "公益专区"}).json()] == ["社区公益包"]


def test_goods_requires_address(client, db):
    h = _rich_user(client, db)
    belt = _product(client, "艾草暖腰带")
    r = client.post("/api/v1/orders", json={"product_id": belt["id"]}, headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == "请填写收货地址（收货人、手机号、详细地址）"
    r = client.post("/api/v1/orders", json={"product_id": belt["id"], "address": {"name": "王"}}, headers=h)
    assert r.status_code == 400
    assert balance(client, h) == 5100
    assert _product(client, "艾草暖腰带")["stock"] == 999


def test_goods_order_and_ship(client, db):
    h = _rich_user(client, db)
    belt = _product(client, "艾草暖腰带")
    r = client.post("/api/v1/orders", json={"product_id": belt["id"], "quantity": 2, "address": ADDRESS}, headers=h)
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["status"] == "pending_shipment" and order["status_text"] == "待发货"
    assert order["total_price"] == 1360 and order["quantity"] == 2
    assert order["address"] == ADDRESS
    assert order["tracking_no"] is None
    assert order["product"]["name"] == "艾草暖腰带"
    assert balance(client, h) == 5100 - 1360
    assert _product(client, "艾草暖腰带")["stock"] == 997
    ledger = client.get("/api/v1/flowers/ledger", headers=h).json()["items"][0]
    assert ledger["reason"] == "redeem" and ledger["delta"] == -1360 and ledger["reason_text"] == "商城兑换"

    pending = client.get("/api/v1/admin/orders", headers=ADMIN).json()
    assert [o["id"] for o in pending["items"]] == [order["id"]] and pending["total"] == 1
    assert pending["items"][0]["user_nickname"] and pending["items"][0]["user_id"]
    r = client.post(f"/api/v1/admin/orders/{order['id']}/ship", json={"tracking_no": "SF123"}, headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] == "shipped" and r.json()["status_text"] == "已发货" and r.json()["tracking_no"] == "SF123"
    # shipped orders cannot be cancelled or shipped again
    r = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h)
    assert r.status_code == 400 and r.json()["detail"] == "只有待发货的订单可以取消"
    assert client.post(f"/api/v1/admin/orders/{order['id']}/ship", json={}, headers=ADMIN).status_code == 400
    assert client.post("/api/v1/admin/orders/9999/ship", json={}, headers=ADMIN).status_code == 404
    mine = client.get("/api/v1/me/orders", headers=h).json()
    assert [o["status"] for o in mine] == ["shipped"]


def test_charity_completes_immediately(client):
    h = login(client)
    charity = _product(client, "社区公益包")
    r = client.post("/api/v1/orders", json={"product_id": charity["id"], "address": ADDRESS}, headers=h)
    assert r.status_code == 400 and r.json()["detail"] == "小红花余额不足"  # 100 < 300
    assert balance(client, h) == 100
    # earn enough: 4 approvals × 50, but only 3 enroll bonuses a day → 330
    for eid in (1, 2, 3, 4):
        sid = submit(client, h, event_id=eid).json()["id"]
        approve(client, sid)
    assert balance(client, h) == 100 + 3 * 10 + 4 * 50 == 330
    r = client.post("/api/v1/orders", json={"product_id": charity["id"]}, headers=h)
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["status"] == "completed" and o["status_text"] == "已完成" and o["address"] is None
    assert balance(client, h) == 330 - 300
    r = client.post(f"/api/v1/orders/{o['id']}/cancel", headers=h)
    assert r.status_code == 400


def test_order_insufficient_balance(client):
    h = login(client)
    belt = _product(client, "艾草暖腰带")
    r = client.post("/api/v1/orders", json={"product_id": belt["id"], "address": ADDRESS}, headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == "小红花余额不足"
    assert balance(client, h) == 100
    assert _product(client, "艾草暖腰带")["stock"] == 999
    assert client.get("/api/v1/me/orders", headers=h).json() == []


def test_order_validation(client, db):
    h = _rich_user(client, db)
    belt = _product(client, "艾草暖腰带")
    assert client.post("/api/v1/orders", json={"product_id": 9999, "address": ADDRESS}, headers=h).status_code == 404
    for q in (0, 100):
        r = client.post("/api/v1/orders", json={"product_id": belt["id"], "quantity": q, "address": ADDRESS}, headers=h)
        assert r.status_code == 400
    assert client.post("/api/v1/orders", json={"product_id": belt["id"], "address": ADDRESS}).status_code == 401


def test_out_of_stock(client, db):
    from app.models import Product

    h = _rich_user(client, db)
    belt = _product(client, "艾草暖腰带")
    db.get(Product, belt["id"]).stock = 1
    db.commit()
    r = client.post("/api/v1/orders", json={"product_id": belt["id"], "quantity": 2, "address": ADDRESS}, headers=h)
    assert r.status_code == 400 and r.json()["detail"] == "库存不足"


def test_cancel_refunds_and_restores_stock(client, db):
    h = _rich_user(client, db)
    bag = _product(client, "银龄出行包")
    order = client.post("/api/v1/orders", json={"product_id": bag["id"], "quantity": 3, "address": ADDRESS}, headers=h).json()
    assert balance(client, h) == 5100 - 2580
    assert _product(client, "银龄出行包")["stock"] == 996

    other = login(client, "someone-else")
    assert client.post(f"/api/v1/orders/{order['id']}/cancel", headers=other).status_code == 404

    r = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled" and r.json()["status_text"] == "已取消"
    assert r.json()["product"]["stock"] == 999
    assert balance(client, h) == 5100
    assert _product(client, "银龄出行包")["stock"] == 999
    top = client.get("/api/v1/flowers/ledger", headers=h).json()["items"][0]
    assert top["reason"] == "refund" and top["delta"] == 2580 and top["reason_text"] == "订单退回"
    # double cancel → no second refund
    assert client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h).status_code == 400
    assert balance(client, h) == 5100
