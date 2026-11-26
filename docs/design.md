# 龄花里小程序 · 设计与接口契约

UI 来源：`ui/dist/index.html`（H5 原型）。本文件是小程序（`miniprogram/`）和后端（`server/`）之间的唯一契约。

## 范围

- 原生微信小程序，只做用户端：发现、赛事、赛事详情、投稿、小红花、商城、我的（+ 我的作品 / 我的订单 / 小红花账本 / 编辑资料）。
- 小程序不做原型里的「封面管理」页；运营使用后端托管的网页后台 `/admin/`（调用 admin API，`X-Admin-Token`），设计见 `docs/superpowers/specs/2026-11-26-admin-console-design.md`。
- 投稿不上传视频，只提交**视频号视频链接**。审核**通过时必须**补充 `feed_token`（用于 `<channel-video>`），或 `finder_user_name` + `feed_id`（用于 `wx.openChannelsActivity`），否则 400 `请填写视频 token，或视频号 ID 与 feed_id`；驳回不要求。
- 图片全部走网络地址：后端返回完整 URL，前缀由 `ASSET_BASE_URL` 配置。开发期由后端 `/static/assets/` 直接托管；上线换 CDN。

## 技术栈

- 小程序：原生 WXML/WXSS/JS，自定义 tabBar，`appid = wx8438a00a54f5b94b`。
- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + PostgreSQL（psycopg 3）+ Alembic，uv 管理依赖，pytest（SQLite）测试。
- 鉴权：`wx.login` → `POST /api/v1/auth/login` → 后端 `jscode2session` 换 openid → 签发 JWT（HS256）。`WECHAT_MOCK_LOGIN=true` 时不调微信，openid 固定为 `mock_dev_user`（或请求体里的 `dev_openid`）。

## 业务规则

| 事件 | 小红花 | 成长值 |
| --- | --- | --- |
| 新用户注册 | +100（`signup_bonus`） | 0 |
| 首次报名某赛事 | +10（`enroll_bonus`，每人每天最多 3 次），赛事 `participant_count` +1（不受限） | +10 |
| 投稿审核通过（每条一次） | +50（`submission_approved`） | +50 |
| 给作品送花 n 朵 | 送花人 −n（`send_flower`），作者 +n（`receive_flower`） | 送花人 +n，作者 +n |
| 商城兑换 | −price×qty（`redeem`） | 0 |
| 取消待发货订单 | +退回（`refund`） | 0 |

- 送花：不能送给自己的作品；n 取 1–99；只能送给已通过审核的作品；同一送花人给同一作者每天最多 20 朵（超出 400，提示今天还能送几朵）；同时累加 `submission.flower_count` 和 `event.flower_count`。
- 「每天」按北京时间自然日（UTC+8）计算。上限常量在 `server/app/rules.py`：`ENROLL_BONUS_DAILY_LIMIT`、`DAILY_GIFT_LIMIT_PER_AUTHOR`。
- 同一条视频链接（规范化后完全相同）全站只能对应一条「审核中 / 已通过」的投稿，跨用户、跨赛事都算；被驳回后可重新投稿。链接先规范化再比较：scheme / host 转小写，去掉默认端口、`#` 片段和末尾 `/`，path 和 query 保持原样。数据库有部分唯一索引 `uq_submissions_live_video` 兜底。同一视频的短链可能每次复制都不同，所以审核通过时还会比对运营补充的 `finder_user_name + feed_id` 或 `feed_token`；如果和另一条审核中或已通过的投稿相同，返回 400 `这条视频与作品 #N 是同一条视频，请驳回本条投稿`。自己重复投 → `这条视频已经投过稿了，同一条视频只能参加一个赛事`；别人已投 → `这条视频已被其他用户投稿，如有疑问请联系客服`。
- 城市：新用户 `city` 为空（未设置）；写入和 `/rankings?city=` 查询都会去掉末尾的「市」（`杭州市` → `杭州`），所以地区选择器和手填的写法能对上。
- 余额变动必须写 `flower_ledger`（`delta`, `reason`, `balance_after`, `ref_type`, `ref_id`），扣减时对 user 行加锁（`SELECT … FOR UPDATE`），余额不能为负。
- 等级（按成长值）：0 银龄新人 / 300 社区新星 / 1000 银龄新星 / 3000 龄花达人 / 8000 龄花名家。
- 投稿会自动报名该赛事。
- 视频链接校验：必须是 `https`，host 为 `weixin.qq.com`、`*.weixin.qq.com`（含 `channels.weixin.qq.com`）或 `finder.video.qq.com`；否则 400，`detail = "请粘贴视频号视频链接（weixin.qq.com / channels.weixin.qq.com）"`。
- 商品 `kind = goods` 需要收货地址，订单状态 `pending_shipment → shipped`；`kind = charity` 不需要地址，订单直接 `completed`。

## 种子数据

- 15 个分类、110 个赛事、封面选择规则、奖励文案、热度 / 参与人数 / AI 标签 / 视频号状态的计算公式：全部照搬 `ui/dist/index.html` 第 587–807 行（`categoryMeta`、`categoryIconKeys`、`categoryRewards`、`themeSceneFiles`、`eventRows`、`eventCatalog` 的 map 逻辑）。分类图片用 `.webp` 版本（如 `category-talent.webp`）。
- 商品 5 个（`featured` 的 4 个出现在首页「参加赛事，赢取好礼」）：

| name | category | kind | price | image | subtitle | reward_desc | featured |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 艾草暖腰带 | 暖心日用 | goods | 680 | reward-warm-belt.webp | 适合日常保暖与送长辈 | 健康打卡、太极和健步走赛季奖励 | ✓ |
| 轻食食养礼盒 | 食养好物 | goods | 520 | reward-food-box.webp | 把安心食材带回家 | 家常菜、面点和节气食养赛事奖励 | ✓ |
| 手作工具包 | 暖心日用 | goods | 520 | reward-craft-kit.webp | 木作、书法、剪纸都用得上 | 木作、书法、剪纸和编织赛季奖励 | ✓ |
| 银龄出行包 | 暖心日用 | goods | 860 | reward-travel-bag.webp | 轻便收纳，陪你走得更远 | 慢旅行、摄影和骑行赛事奖励 | ✓ |
| 社区公益包 | 公益专区 | charity | 300 | reward-craft-kit.webp | 把一份心意送到需要的地方 | 社区公益项目 | ✗ |

库存默认 999。

## 接口（前缀 `/api/v1`）

通用：JSON；鉴权头 `Authorization: Bearer <token>`；错误统一 `{"detail": "中文提示"}`（400 业务错误 / 401 未登录 / 403 / 404）。时间为 ISO8601 字符串。分页参数 `page`（从 1 起）、`page_size`（默认 20，最大 100），分页响应 `{"items": [...], "total": n}`。标注「可选鉴权」的接口带 token 时返回与当前用户相关的字段。

### 对象

```jsonc
// User
{ "id": 1, "nickname": "银龄生活家", "avatar_url": "https://…|null", "city": "", "district": "", "community": "",
  "flower_balance": 110, "growth_value": 10, "level_name": "银龄新人", "next_level_name": "社区新星", "next_level_value": 300,
  "enrolled_count": 1, "submission_count": 0, "created_at": "…" }

// Category
{ "name": "才艺", "note": "唱跳、器乐与舞台表达", "icon_key": "microphone", "image_url": "…/category-talent.webp", "event_count": 6 }

// Event
{ "id": 1, "title": "银龄才艺开放麦", "category": "才艺", "desc": "…", "geo": "城市→社区组", "status_text": "报名进行中",
  "emoji": "🎤", "icon_key": "microphone", "cover_url": "…", "heat": 97, "participant_count": 818, "flower_count": 1280,
  "reward_text": "舞台麦克风支架 · 420 朵", "ai_allowed": false, "ai_label": "原声/实拍优先",
  "track": "才艺 · 城市 / 社区组", "video_status": "已接入测试 · 待验证", "enrolled": false }

// Submission
{ "id": 1, "event_id": 1, "event_title": "银龄才艺开放麦", "title": "…", "description": "…", "video_url": "https://…",
  "finder_user_name": null, "feed_id": null, "feed_token": null,
  "status": "pending|approved|rejected", "reject_reason": null, "flower_count": 0,
  "author": { "id": 1, "nickname": "…", "avatar_url": null, "city": "杭州" }, "created_at": "…" }

// LedgerEntry
{ "id": 1, "delta": 100, "reason": "signup_bonus", "reason_text": "新人礼", "balance_after": 100, "note": null, "created_at": "…" }  // note：运营调整的备注
// reason_text: signup_bonus 新人礼 / enroll_bonus 报名奖励 / submission_approved 投稿通过 / send_flower 送出小红花 /
//              receive_flower 收到小红花 / redeem 商城兑换 / refund 订单退回 / admin_adjust 运营调整

// Product
{ "id": 1, "name": "艾草暖腰带", "subtitle": "…", "reward_desc": "…", "category": "暖心日用", "kind": "goods",
  "price": 680, "image_url": "…", "stock": 999, "featured": true }

// Order
{ "id": 1, "product": Product, "quantity": 1, "total_price": 680,
  "status": "pending_shipment|shipped|completed|cancelled", "status_text": "待发货|已发货|已完成|已取消",
  "address": { "name": "", "phone": "", "province": "", "city": "", "district": "", "detail": "" } | null,
  "tracking_no": null, "created_at": "…" }
```

### 路由

| 方法 | 路径 | 鉴权 | 请求 | 响应 |
| --- | --- | --- | --- | --- |
| GET | `/health` | – | – | `{"ok": true}` |
| POST | `/auth/login` | – | `{"code": "...", "dev_openid"?: "..."}` | `{"token": "...", "user": User}` |
| GET | `/me` | ✓ | – | `User` |
| PATCH | `/me` | ✓ | `{nickname?, avatar_url?, city?, district?, community?}` | `User` |
| POST | `/me/avatar` | ✓ | multipart `file`（≤2MB 图片） | `{"avatar_url": "..."}` |
| GET | `/categories` | – | – | `Category[]` |
| GET | `/events/summary` | – | – | `{"event_count": 110, "category_count": 15, "geo_levels": 6}` |
| GET | `/events` | 可选 | `?category=&featured=1&page=&page_size=` | 分页 `Event`；`featured=1` 返回首页 6 个（原型索引 0,6,12,18,24,30） |
| GET | `/events/{id}` | 可选 | – | `Event` |
| POST | `/events/{id}/enroll` | ✓ | – | `{"enrolled": true, "first_time": bool, "bonus": 10\|0, "participant_count": n, "flower_balance": n}`（`bonus` 为本次实际发放，重复报名或当日已满 3 次为 0） |
| GET | `/events/{id}/submissions` | – | `?page=&page_size=` | 分页 `Submission`（仅 approved，按 flower_count 降序） |
| GET | `/me/enrollments` | ✓ | – | `Event[]` |
| POST | `/submissions` | ✓ | `{"event_id", "title", "description"?, "video_url"}` | `Submission`（pending） |
| GET | `/submissions/{id}` | 可选 | – | `Submission`（非 approved 只有作者能看） |
| GET | `/me/submissions` | ✓ | – | `Submission[]` |
| POST | `/submissions/{id}/flowers` | ✓ | `{"count": 1}` | `{"flower_balance": n, "submission_flower_count": n}` |
| GET | `/flowers/ledger` | ✓ | `?page=&page_size=` | `{"balance": n, "items": LedgerEntry[], "total": n}` |
| GET | `/rankings` | – | `?city=&category=&limit=20` | `[{"rank", "submission_id", "author_id", "title", "event_title", "author_nickname", "author_avatar_url", "city", "flower_count"}]` |
| GET | `/products` | – | `?category=&featured=1` | `Product[]` |
| POST | `/orders` | ✓ | `{"product_id", "quantity"?: 1, "address"?: {...}}` | `Order` |
| GET | `/me/orders` | ✓ | – | `Order[]` |
| POST | `/orders/{id}/cancel` | ✓ | – | `Order` |
| GET | `/admin/stats` | admin | – | `{"pending_submissions", "pending_shipments", "users_today", "flowers_today"}` |
| GET | `/admin/submissions` | admin | `?status=pending&q=&page=` | `{"items": Submission[], "total"}` |
| POST | `/admin/submissions/{id}/review` | admin | `{"action": "approve|reject", "reason"?, "finder_user_name"?, "feed_id"?, "feed_token"?}`（approve 须有 token 或 ID+feed_id） | `Submission` |
| PATCH | `/admin/submissions/{id}` | admin | 任意 `finder_user_name, feed_id, feed_token` | `Submission` |
| GET | `/admin/orders` | admin | `?status=pending_shipment&page=` | `{"items": Order + {"user_id", "user_nickname"}[], "total"}` |
| POST | `/admin/orders/{id}/ship` | admin | `{"tracking_no"?: "..."}` | `Order` |
| GET | `/admin/events` | admin | `?q=&category=&featured=&page=` | `{"items": Event + {"featured", "sort_order"}[], "total"}` |
| PATCH | `/admin/events/{id}` | admin | 任意 `heat, participant_count, flower_count, reward_text, ai_allowed, ai_label, track, video_status, cover_url, featured` | `Event + {"featured", "sort_order"}` |
| GET | `/admin/users` | admin | `?q=`（昵称模糊或用户 ID）`&page=` | `{"items": User + {"openid"}[], "total"}` |
| GET | `/admin/users/{id}/ledger` | admin | `?page=` | 同 `/flowers/ledger` |
| POST | `/admin/users/{id}/flowers` | admin | `{"delta": ±n（≠0，绝对值 ≤100000）, "note": "必填"}`，记 `admin_adjust`，不改成长值 | `User + {"openid"}` |

## 配置（后端环境变量，`server/.env`）

`DATABASE_URL`（默认 `postgresql+psycopg://localhost/linghuali`）、`JWT_SECRET`、`WECHAT_APPID`、`WECHAT_SECRET`、`WECHAT_MOCK_LOGIN`（默认 true）、`ASSET_BASE_URL`（默认 `http://127.0.0.1:8001/static/assets/`）、`UPLOAD_BASE_URL`（默认 `http://127.0.0.1:8001/static/uploads/`）、`ADMIN_TOKEN`、`CORS_ORIGINS`。

## 小程序配置

`miniprogram/config.js`：`API_BASE`（默认 `http://127.0.0.1:8001/api/v1`）。开发者工具需勾选「不校验合法域名」（`project.config.json` 已设 `urlCheck: false`）。
