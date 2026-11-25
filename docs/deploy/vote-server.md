# vote.jh8.ai 部署手册

服务器：AWS 香港 18.162.184.136（Ubuntu 24.04），用 `ubuntu` 账号登录（免密 sudo）。同机还有 outfit、qpred 等服务和宝塔 nginx 上的其他站点，本项目只新增自己的用户、目录、服务、数据库和站点配置，不改它们。

- 系统用户 `vote`，目录 `/www/wwwroot/vote`：`app/`（代码、`.venv`、图片 `static/assets`）、`uploads/`（用户上传的头像，`app/static/uploads` 是指向它的软链接，发布不会删）、`.env`（配置，600）。
- 服务 `vote-api`：uvicorn，监听 `127.0.0.1:8030`，2 个 worker。
- 数据库：宝塔装的 PostgreSQL 18（`/www/server/pgsql`，只听本机 5432）：库 `linghuali`，属主角色 `vote`。手动查库：`cd /tmp && sudo -u postgres /www/server/pgsql/bin/psql linghuali`。
- 站点：宝塔站点 `vote.jh8.ai`，配置文件 `/www/server/panel/vhost/nginx/html_vote.jh8.ai.conf`，证书由面板签发和续期（`/www/server/panel/vhost/cert/vote.jh8.ai/`）。

## 一、首次部署

1. 开发机：`ssh ubuntu@18.162.184.136 sudo bash -s -- vote.jh8.ai < deploy/bootstrap.sh`。建用户和目录、装 uv 和 Python 3.12、建 Postgres 角色和库，并生成 `.env`（随机 `JWT_SECRET`、`ADMIN_TOKEN` 和数据库密码，`WECHAT_MOCK_LOGIN=false`）。
2. 服务器：`sudo -e /www/wwwroot/vote/.env` 填 `WECHAT_SECRET`（小程序后台 → 开发管理 → 开发设置），然后 `sudo systemctl restart vote-api`。不填时小程序登录会失败，其余接口和后台正常。
3. 开发机：`deploy/deploy.sh`（见第二节）。
4. nginx：`ssh ubuntu@18.162.184.136 sudo bash /www/wwwroot/vote/app/deploy/patch-nginx.sh`，它按 `deploy/nginx-vote.jh8.ai.conf` 改站点配置（可重复执行，`nginx -t` 不过会自动还原）。删掉面板默认的两个静态文件正则块（不删的话 `/admin/app.js` 和图片会去空的站点根目录找，返回 404），在原位置放 `#VOTE-API-START…END` 之间的内容；保留面板的证书、HTTPS 跳转和 well-known 段。改前先备份到 `/root/vote-nginx-backup/`，然后 `/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload`。注意：在面板里改这个站点的设置（比如重新开关 SSL）可能重写这个文件，改完检查这一段还在。
5. 验证：`curl https://vote.jh8.ai/api/v1/health` 返回 `{"status":"ok"}`；打开 <https://vote.jh8.ai/admin/>，用 `.env` 里的 `ADMIN_TOKEN` 登录（`sudo grep ADMIN_TOKEN /www/wwwroot/vote/.env`）。

## 二、发布新版本

开发机：`deploy/deploy.sh`（默认 `ubuntu@18.162.184.136`）。只从干净的 `origin/main` 发布（`deploy/require-main.sh`）。脚本会 rsync `server/`（含 `static/assets` 图片，它不在 git 里；新克隆的仓库先 `cd server && uv run python scripts/sync_assets.py`）、`uv sync`、`alembic upgrade head`、`python -m app.seed`（幂等，不覆盖已有数据）、装 systemd 单元、重启并检查 `/api/v1/health`。

回滚：在 main 上 `git revert`，推送后再发布。迁移只向前，回滚不会撤销已应用的迁移。

## 三、日常

- 日志：`sudo journalctl -u vote-api -f`；nginx 访问日志 `/www/wwwlogs/vote.jh8.ai.log`。
- 运营后台：<https://vote.jh8.ai/admin/>。换管理员令牌：改 `.env` 的 `ADMIN_TOKEN` 后重启 `vote-api`。
- 接口文档：<https://vote.jh8.ai/docs>。

## 四、小程序侧

`miniprogram/config.js` 的 trial / release 指向 `https://vote.jh8.ai/api/v1` 和 `https://vote.jh8.ai/static/assets/`。在小程序后台「开发管理 → 开发设置 → 服务器域名」把 `https://vote.jh8.ai` 加到 request、uploadFile、downloadFile 合法域名。
