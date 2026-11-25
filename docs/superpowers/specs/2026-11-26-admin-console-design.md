# 运营后台（Admin Console）设计

## 目的

运营目前只能在 Swagger 里手调 admin 接口。做一个能日常使用的网页后台：审核投稿（补视频号 token）、订单发货、赛事运营、查用户并调整小红花。

## 目标 / 非目标

- 目标：概览、投稿审核、订单发货、赛事运营、用户与小红花五个模块；审核通过必须带视频号信息。
- 非目标：商品管理（上下架/库存）、多管理员账号与权限、操作审计。
- 反目标：绕过业务规则直接改表（审核加花、账本、库存退回必须走现有 service）。

## 方案（已选：A）

- **A. FastAPI 直接托管的静态页（原生 HTML/JS，无构建、无外部 CDN）** —— 选中：与后端同仓同进程，零构建，规模合适。
- B. 独立 Vue/React 项目 —— 多一套构建与部署，对 5 个页面过重。
- C. sqladmin 等自动 CRUD —— 绕过业务规则（加花、账本、退库存）。

## 设计

- 页面：`server/admin/index.html` + `app.js` + `app.css`，挂载于 `/admin/`。登录 = 输入管理员令牌，存 `localStorage`，所有请求带 `X-Admin-Token`；403 时回到登录。
- **审核规则（后端强制）**：`action=approve` 时必须有 `feed_token`，或同时有 `finder_user_name` 和 `feed_id`（可来自本次请求或投稿已有值），否则 400 `请填写视频 token，或视频号 ID 与 feed_id`。驳回不要求。
- 表单：「视频 token」第一位且必填；「视频号 ID + feed_id」折叠为备选；驳回需填原因。
- 新增/扩展接口（均需 admin）：
  - `GET /admin/stats` → `{pending_submissions, pending_shipments, users_today, flowers_today}`（今日按中国时区）。
  - `GET /admin/submissions` 增加分页 `page/page_size` 与 `q`（标题/作者昵称），返回 `{items,total}`。
  - `PATCH /admin/submissions/{id}` 仅改 `finder_user_name/feed_id/feed_token`，同样做 feed 去重；已通过的投稿改后仍需满足视频号信息必填。
  - `GET /admin/orders` 增加分页，返回 `{items,total}`，订单带下单用户（id、昵称）。
  - `GET /admin/events?q=&page=` 管理用赛事列表（含 `featured`、`sort_order`）；`EventPatch` 增加 `featured`。
  - `GET /admin/users?q=&page=`（昵称模糊 / 精确 id）、`GET /admin/users/{id}/ledger`、`POST /admin/users/{id}/flowers` `{delta, note}`（delta≠0，note 必填，记 `admin_adjust`，不改成长值，余额不可为负）。
- 账本新增 `note` 字段（迁移 0003），调整备注写入其中并在账本中返回。

## 留给实现者

样式细节、分页大小（默认 20）、列表字段取舍。
