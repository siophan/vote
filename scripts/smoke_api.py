"""End-to-end smoke test of the API, following the mini-program's call sequence.

Checks that every field the mini-program pages read is present. Requires a running
server with WECHAT_MOCK_LOGIN=true. Creates throwaway users (random dev_openid).

Usage: python3 scripts/smoke_api.py [--base http://127.0.0.1:8001/api/v1] [--admin-token TOKEN]
"""
import argparse
import json
import random
import string
import sys
import urllib.error
import urllib.parse
import urllib.request

FIELDS = {
    "user": ["id", "nickname", "avatar_url", "city", "district", "community", "flower_balance", "growth_value",
             "level_name", "next_level_name", "next_level_value", "enrolled_count", "submission_count"],
    "category": ["name", "note", "icon_key", "image_url", "event_count"],
    "event": ["id", "title", "category", "desc", "geo", "status_text", "emoji", "icon_key", "cover_url", "heat",
              "participant_count", "flower_count", "reward_text", "ai_allowed", "ai_label", "track", "video_status",
              "enrolled"],
    "submission": ["id", "event_id", "event_title", "title", "description", "video_url", "finder_user_name", "feed_id",
                   "feed_token", "status", "reject_reason", "flower_count", "author", "created_at"],
    "author": ["id", "nickname", "avatar_url", "city"],
    "ledger": ["id", "delta", "reason", "reason_text", "balance_after", "created_at"],
    "product": ["id", "name", "subtitle", "reward_desc", "category", "kind", "price", "image_url", "stock", "featured"],
    "order": ["id", "product", "quantity", "total_price", "status", "status_text", "address", "tracking_no",
              "created_at"],
    "ranking": ["rank", "submission_id", "author_id", "title", "event_title", "author_nickname", "author_avatar_url", "city",
                "flower_count"],
}

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def has_fields(obj, kind):
    missing = [f for f in FIELDS[kind] if f not in obj]
    check(not missing, f"{kind} fields" + (f" missing {missing}" if missing else ""))


class Client:
    def __init__(self, base, token=None, admin=None):
        self.base, self.token, self.admin = base, token, admin

    def call(self, method, path, body=None, expect=200):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + urllib.parse.quote(path, safe="/?=&"), data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        if self.admin:
            req.add_header("X-Admin-Token", self.admin)
        try:
            with urllib.request.urlopen(req) as res:
                status, payload = res.status, json.loads(res.read() or b"null")
        except urllib.error.HTTPError as err:
            status, payload = err.code, json.loads(err.read() or b"null")
        check(status == expect, f"{method} {path} -> {status} (want {expect})"
              + ("" if status == expect else f" {payload}"))
        return payload


def login(base, tag):
    openid = "smoke_" + tag + "_" + "".join(random.choices(string.ascii_lowercase, k=8))
    res = Client(base).call("POST", "/auth/login", {"code": "smoke", "dev_openid": openid})
    has_fields(res["user"], "user")
    return Client(base, res["token"]), res["user"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001/api/v1")
    ap.add_argument("--admin-token", default="dev-admin-token")
    args = ap.parse_args()
    base = args.base
    admin = Client(base, admin=args.admin_token)

    print("[public catalog]")
    anon = Client(base)
    anon.call("GET", "/health")
    cats = anon.call("GET", "/categories")
    check(len(cats) == 15, f"15 categories (got {len(cats)})")
    has_fields(cats[0], "category")
    summary = anon.call("GET", "/events/summary")
    check(summary == {"event_count": 110, "category_count": 15, "geo_levels": 6}, f"summary {summary}")
    featured = anon.call("GET", "/events?featured=1")
    items = featured["items"] if isinstance(featured, dict) else featured
    check([e["title"] for e in items][:2] == ["银龄才艺开放麦", "我的银龄活力日"], "featured order matches prototype")
    has_fields(items[0], "event")
    page = anon.call("GET", "/events?category=才艺&page=1&page_size=100")
    check(page["total"] == 6 and len(page["items"]) == 6, "category filter 才艺 = 6")
    products = anon.call("GET", "/products?featured=1")
    check(len(products) == 4, "4 featured products")
    has_fields(products[0], "product")
    check(len(anon.call("GET", "/products?category=公益专区")) == 1, "公益专区 has 1 product")
    req = urllib.request.Request(items[0]["cover_url"], method="HEAD")
    try:
        with urllib.request.urlopen(req) as r:
            check(r.status == 200, "event cover image served")
    except urllib.error.HTTPError as e:
        check(False, f"event cover image served ({e.code})")

    print("[author: enroll + submit]")
    alice, alice_user = login(base, "alice")
    check(alice_user["flower_balance"] == 100, "signup bonus 100")
    alice.call("PATCH", "/me", {"nickname": "桂香阿姨", "city": "杭州市", "district": "西湖区", "community": "翠苑一区"})
    event_id = items[0]["id"]
    first = alice.call("POST", f"/events/{event_id}/enroll")
    check(first["first_time"] is True and first["bonus"] == 10 and first["flower_balance"] == 110, "first enroll +10")
    again = alice.call("POST", f"/events/{event_id}/enroll")
    check(again["first_time"] is False and again["bonus"] == 0 and again["flower_balance"] == 110, "re-enroll no bonus")
    check(alice.call("GET", f"/events/{event_id}")["enrolled"] is True, "event.enrolled true for author")
    alice.call("POST", "/submissions", {"event_id": event_id, "title": "x", "video_url": "https://example.com/v"}, expect=400)
    link = "https://weixin.qq.com/sph/smoke" + "".join(random.choices(string.ascii_letters, k=10))
    sub = alice.call("POST", "/submissions", {"event_id": event_id, "title": "二胡《赛马》", "description": "老周的二胡",
                                              "video_url": link})
    has_fields(sub, "submission")
    has_fields(sub["author"], "author")
    check(sub["status"] == "pending", "submission pending")
    other_event = items[1]["id"]
    alice.call("POST", "/submissions", {"event_id": other_event, "title": "同一条", "video_url": link}, expect=400)
    check(len(alice.call("GET", "/me/submissions")) == 1, "me/submissions lists it (duplicate video blocked)")
    check(len(alice.call("GET", "/me/enrollments")) >= 1, "me/enrollments")

    print("[admin review]")
    Client(base).call("GET", "/admin/submissions?status=pending", expect=403)
    pend = admin.call("GET", "/admin/submissions?status=pending")
    check(any(s["id"] == sub["id"] for s in pend["items"]), "pending list has submission")
    admin.call("POST", f"/admin/submissions/{sub['id']}/review", {"action": "approve"}, expect=400)  # needs 视频号 info
    approved = admin.call("POST", f"/admin/submissions/{sub['id']}/review",
                          {"action": "approve", "finder_user_name": "sphTest", "feed_id": "export/" + link[-10:],
                           "feed_token": "smoke-" + link[-10:]})
    check(approved["status"] == "approved", "approved")
    check(alice.call("GET", "/me")["flower_balance"] == 160, "approval bonus +50")

    print("[fan: send flowers]")
    bob, _ = login(base, "bob")
    bob.call("POST", f"/submissions/{sub['id']}/flowers", {"count": 1000}, expect=400)
    sent = bob.call("POST", f"/submissions/{sub['id']}/flowers", {"count": 5})
    check(sent == {"flower_balance": 95, "submission_flower_count": 5}, f"send 5 -> {sent}")
    alice.call("POST", f"/submissions/{sub['id']}/flowers", {"count": 1}, expect=400)
    check(alice.call("GET", "/me")["flower_balance"] == 165, "author received +5")
    bob.call("POST", f"/submissions/{sub['id']}/flowers", {"count": 16}, expect=400)  # 5 + 16 > 20 per author per day
    works = anon.call("GET", f"/events/{event_id}/submissions")
    check(any(w["id"] == sub["id"] for w in works["items"]), "approved work listed on event")
    ranks = anon.call("GET", "/rankings?city=杭州市&limit=20")
    check(any(r["submission_id"] == sub["id"] for r in ranks), "rankings by city include work")
    if ranks:
        has_fields(ranks[0], "ranking")

    print("[mall]")
    all_products = anon.call("GET", "/products")
    goods = min((p for p in all_products if p["kind"] == "goods"), key=lambda p: p["price"])
    charity = next(p for p in all_products if p["kind"] == "charity")
    address = {"name": "张桂香", "phone": "13800000000", "province": "浙江省", "city": "杭州市",
               "district": "西湖区", "detail": "翠苑一区 1 幢"}
    alice.call("POST", "/orders", {"product_id": goods["id"], "address": address}, expect=400)  # 165 < price
    # earn enough for goods: 7 more approved works (+50 each); only 2 more enroll bonuses today (3/day)
    more = [e["id"] for e in anon.call("GET", "/events?page=1&page_size=12")["items"] if e["id"] != event_id][:7]
    for i, eid in enumerate(more):
        extra = alice.call("POST", "/submissions", {"event_id": eid, "title": f"作品{i}", "video_url": f"{link}x{i}"})
        admin.call("POST", f"/admin/submissions/{extra['id']}/review",
                   {"action": "approve", "feed_token": f"smoke-{link[-10:]}-{i}",
                    "finder_user_name": "sphTest", "feed_id": f"export/{link[-10:]}-{i}"})
    bal = alice.call("GET", "/me")["flower_balance"]
    check(bal == 165 + 7 * 50 + 2 * 10, f"balance after approvals {bal}")
    alice.call("POST", "/orders", {"product_id": goods["id"]}, expect=400)  # goods needs address
    order = alice.call("POST", "/orders", {"product_id": goods["id"], "address": address})
    has_fields(order, "order")
    check(order["status"] == "pending_shipment", "goods order pending_shipment")
    check(alice.call("GET", "/me")["flower_balance"] == bal - goods["price"], "redeem deducted")
    cancelled = alice.call("POST", f"/orders/{order['id']}/cancel")
    check(cancelled["status"] == "cancelled", "cancelled")
    check(alice.call("GET", "/me")["flower_balance"] == bal, "refund restored balance")
    alice.call("POST", f"/orders/{order['id']}/cancel", expect=400)
    order2 = alice.call("POST", "/orders", {"product_id": charity["id"]})
    check(order2["status"] == "completed" and order2["address"] is None, "charity order completed")
    order3 = alice.call("POST", "/orders", {"product_id": goods["id"], "address": address}, expect=400)  # 235 < 520
    check(len(alice.call("GET", "/me/orders")) == 2, "me/orders lists 2")
    shipped = admin.call("POST", f"/admin/orders/{order2['id']}/ship", {"tracking_no": "SF123"}, expect=400)

    print("[admin console APIs]")
    stats = admin.call("GET", "/admin/stats")
    check(set(stats) == {"pending_submissions", "pending_shipments", "users_today", "flowers_today"}, f"stats {stats}")
    found = admin.call("GET", f"/admin/users?q={alice_user['id']}")
    check(any(u["id"] == alice_user["id"] for u in found["items"]), "admin user search by id")
    adj = admin.call("POST", f"/admin/users/{alice_user['id']}/flowers", {"delta": 5, "note": "smoke 补发"})
    check(adj["flower_balance"] == bal - charity["price"] + 5, "admin adjust +5")
    check(admin.call("GET", "/admin/events?q=开放麦")["total"] >= 1, "admin events search")
    page = urllib.request.urlopen(base.replace("/api/v1", "") + "/admin/")
    check(page.status == 200 and b"app.js" in page.read(), "admin console served at /admin/")

    print("[ledger]")
    ledger = alice.call("GET", "/flowers/ledger?page=1&page_size=30")
    check("balance" in ledger and "total" in ledger, "ledger envelope")
    has_fields(ledger["items"][0], "ledger")
    reasons = {e["reason"] for e in ledger["items"]}
    check({"signup_bonus", "enroll_bonus", "submission_approved", "receive_flower", "redeem", "refund", "admin_adjust"} <= reasons,
          f"ledger reasons {sorted(reasons)}")

    print()
    if failures:
        print(f"{len(failures)} FAILED")
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
