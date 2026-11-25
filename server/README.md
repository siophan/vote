# 龄花里 · 后端（FastAPI）

接口契约见 `../docs/design.md`。前缀 `/api/v1`，静态文件 `/static/assets/*`（种子图片）与 `/static/uploads/*`（头像上传）。

技术栈：Python 3.12 · FastAPI · SQLAlchemy 2.0 · PostgreSQL（psycopg 3）· Alembic · uv · pytest（SQLite）。

## 目录

```
app/
  config.py        pydantic-settings（读 server/.env）
  db.py models.py  SQLAlchemy 引擎 / 模型
  schemas.py       请求与响应模型（契约里的 User / Event / Submission …）
  rules.py         等级、reason_text、视频号链接校验、资源 URL 拼接
  security.py      JWT（HS256）    wechat.py  jscode2session（httpx，支持 mock）
  deps.py          当前用户 / 可选用户 / X-Admin-Token
  services/        ledger（余额 + 账本，行锁）、events（报名）、submissions（投稿/审核/送花）、orders、presenters
  routers/         auth、me、events、submissions（含账本 / 排行）、shop、admin
  seed_data.py     从 ui/dist/index.html 移植的分类 / 110 个赛事 / 计算公式 / 商品
  seed.py          python -m app.seed（幂等）
alembic/           迁移（0001 initial schema）
scripts/sync_assets.py  从 ui/dist/assets/generated 拷贝图片到 static/assets
tests/             pytest
```

## 本地启动

```bash
cd server
uv sync
cp .env.example .env          # 已有 .env 可跳过（本地默认 mock 登录）
createdb linghuali            # 本机 PostgreSQL 17，当前系统用户
uv run python scripts/sync_assets.py
uv run alembic upgrade head
uv run python -m app.seed     # 可重复执行，已存在的数据不覆盖
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

接口文档：<http://127.0.0.1:8001/docs>

## 测试

```bash
uv run pytest
# 可选：同一套测试跑在 PostgreSQL 上（会 drop 该库所有表，务必用一次性库）
createdb linghuali_test
TEST_DATABASE_URL=postgresql+psycopg://localhost/linghuali_test uv run pytest
```

## 配置（`.env`）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://localhost/linghuali` | |
| `JWT_SECRET` | `change-me` | 生产务必修改（≥32 字节） |
| `JWT_EXPIRE_DAYS` | `30` | |
| `WECHAT_APPID` / `WECHAT_SECRET` | | 关闭 mock 后用于 jscode2session |
| `WECHAT_MOCK_LOGIN` | `true` | true 时 openid = 请求体 `dev_openid` 或 `mock_dev_user` |
| `ASSET_BASE_URL` | `http://127.0.0.1:8001/static/assets/` | 图片前缀，上线换 CDN |
| `UPLOAD_BASE_URL` | `http://127.0.0.1:8001/static/uploads/` | 上传文件前缀 |
| `ADMIN_TOKEN` | 空（= 禁用 admin 接口） | admin 接口请求头 `X-Admin-Token` |
| `CORS_ORIGINS` | `*` | 逗号分隔 |

## 常用调试

```bash
BASE=http://127.0.0.1:8001/api/v1
curl $BASE/health
curl "$BASE/events?featured=1"
TOKEN=$(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"code":"dev","dev_openid":"tester_1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl $BASE/me -H "Authorization: Bearer $TOKEN"
curl -X POST $BASE/submissions -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"event_id":1,"title":"我的二胡","video_url":"https://weixin.qq.com/sph/AbCdEf"}'
```

## 运营后台

后端启动后打开 <http://127.0.0.1:8001/admin/>，输入管理员令牌（即 `ADMIN_TOKEN`）登录。页面是 `server/admin/` 下的静态文件（原生 HTML/JS，无需构建），包含：

- **概览**：待审核投稿、待发货订单、今日新用户、今日送出小红花（今日按北京时间）。
- **投稿审核**：按状态筛选、搜索标题/作者；通过时**必须**填视频 token，或视频号 ID + feed_id；驳回需填原因；已通过的作品可修改视频号信息。
- **订单发货**：查看收货地址（可复制）、填快递单号发货。
- **赛事运营**：搜索 / 按分类筛选，切换首页精选，编辑热度、奖励、封面等字段。
- **用户与小红花**：按昵称或 ID 查用户，看账本，增减小红花（备注必填，记为「运营调整」，用户账本可见）。

## 运营（admin）接口

所有 admin 接口需要请求头 `X-Admin-Token: $ADMIN_TOKEN`（本地 `.env` 里是 `dev-admin-token`），否则 403。

```bash
BASE=http://127.0.0.1:8001/api/v1
ADMIN='X-Admin-Token: dev-admin-token'

# 概览数字
curl "$BASE/admin/stats" -H "$ADMIN"

# 待审核投稿（status: pending 默认 / approved / rejected / all；q 搜标题或作者昵称；分页 page/page_size）
curl "$BASE/admin/submissions?status=pending" -H "$ADMIN"

# 审核通过必须带视频号信息：feed_token，或 finder_user_name + feed_id（可沿用投稿上已有的值），
# 否则 400「请填写视频 token，或视频号 ID 与 feed_id」。首次通过作者 +50 小红花 / +50 成长值，重复通过不再发放
curl -X POST $BASE/admin/submissions/1/review -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"action":"approve","finder_user_name":"sphXXXX","feed_id":"export/XXXX"}'
#   或用 <channel-video> 的 feed_token：
curl -X POST $BASE/admin/submissions/1/review -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"action":"approve","feed_token":"XXXX"}'

# 驳回
curl -X POST $BASE/admin/submissions/2/review -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"action":"reject","reason":"链接无法打开，请重新提交"}'

# 待发货订单（扩展接口；status: pending_shipment 默认 / shipped / completed / cancelled / all）
curl "$BASE/admin/orders" -H "$ADMIN"

# 只修改视频号信息（不改状态；已通过的作品改完仍须满足上面的必填规则）
curl -X PATCH $BASE/admin/submissions/1 -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"feed_token":"XXXX"}'

# 发货
curl -X POST $BASE/admin/orders/1/ship -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"tracking_no":"SF1234567890"}'

# 修改赛事展示字段（cover_url 可传文件名 theme-scene-05.webp 或完整 URL）
curl -X PATCH $BASE/admin/events/1 -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"heat":99,"video_status":"支持视频号链接","cover_url":"theme-scene-05.webp","featured":true}'

# 赛事列表（含 featured / sort_order）、用户列表、账本、调整小红花
curl "$BASE/admin/events?q=开放麦&category=才艺" -H "$ADMIN"
curl "$BASE/admin/users?q=桂香" -H "$ADMIN"
curl "$BASE/admin/users/1/ledger" -H "$ADMIN"
curl -X POST $BASE/admin/users/1/flowers -H "$ADMIN" -H 'Content-Type: application/json' \
  -d '{"delta":50,"note":"线下活动补发"}'
```

## 业务规则要点

- 所有余额变动经 `services/ledger.apply_delta`：写 `flower_ledger`（delta / reason / balance_after / ref_type / ref_id），先 `SELECT … FOR UPDATE` 锁用户行，余额不足返回 400 `小红花余额不足`；数据库另有 `flower_balance >= 0`、`stock >= 0` 约束兜底。
- 注册奖励、报名奖励用 `INSERT … ON CONFLICT DO NOTHING` 判定"首次"，并发下也只发一次；投稿通过奖励由 `submissions.approval_bonus_granted` 保证只发一次。
- 送花 / 兑换 / 取消都在单个事务里完成；多用户加锁按 id 升序，避免死锁。
