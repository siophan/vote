# 龄花里 · 微信小程序（原生）

UI 还原自 `ui/dist/index.html`，接口契约见 `docs/design.md`。

## 运行

1. 先启动后端（见 `server/README.md`），默认 `http://127.0.0.1:8001`。
2. 微信开发者工具 → 导入项目 → 目录选 `miniprogram/`（appid 已写在 `project.config.json`）。
3. 「详情 → 本地设置」确认勾选「不校验合法域名…」（`urlCheck: false` 已默认关闭）。
4. 编译即可。启动时会静默 `wx.login`，后端开启 `WECHAT_MOCK_LOGIN` 时不需要真实 AppSecret。

真机预览时 `127.0.0.1` 指向手机自己，需要把 `config.js` 里 `develop.API_BASE` / `ASSET_BASE` 改成电脑的局域网 IP，并让后端监听 `0.0.0.0`。

## 目录

```
config.js              各环境 API_BASE / ASSET_BASE（图片 CDN 前缀）
app.js / app.wxss      全局：静默登录、设计变量与通用样式（px×2 → rpx）
custom-tab-bar/        自定义底部导航（发现 / 赛事 / 小红花 / 商城 / 我的）
components/
  brand-bar/           首页品牌导航栏（自定义导航，避让胶囊按钮）
  event-card/          赛事卡片（waterfall 首页瀑布流 / catalog 赛事中心）
  icon-badge/          金色分类徽章（icon-sprite.webp 精灵图）
pages/
  home/                发现：hero、精选赛事瀑布流、入口、好礼
  events/              赛事中心：统计、分类封面、筛选、分页列表、视频号精选
  event-detail/        赛事详情：报名、去投稿、参赛作品榜、分享
  submit/              投稿：分类→赛事选择、粘贴视频号链接、校验、提交
  work/                作品页：视频号播放/跳转、送花、分享
  flowers/             小红花：账户、用途、全国/同城榜单、一键送花
  mall/                商城：分类、兑换（实物选地址 / 公益直接完成）
  mine/                我的：资料卡、入口、已报名赛事
  works/ orders/ ledger/ profile/   我的作品、订单、账本、编辑资料
utils/
  request.js           wx.request 封装：自动带 token，401 自动重登重试
  auth.js              wx.login → /auth/login，并发去重
  icons.js             SVG 线性图标（由 scripts/gen_icons.py 生成，勿手改）
```

## 视频号

投稿只收视频号视频链接（`https://weixin.qq.com/sph/...` 或 `channels.weixin.qq.com`）。作品页的播放方式按运营审核时补充的信息依次降级：

1. 有 `feed_token` → 页面内 `<channel-video>` 直接播放；
2. 有 `finder_user_name` + `feed_id` → `wx.openChannelsActivity` 跳转视频号；
3. 都没有 → 复制链接，提示在微信聊天中打开。

## 上线前

- `config.js` 的 trial / release 换成正式 https 域名和图片 CDN，并在小程序后台配置 request / uploadFile / downloadFile 合法域名。
- 小程序后台「用户隐私保护指引」声明：收货地址（`wx.chooseAddress`）、头像、昵称、剪贴板。
- 「服务类目」需覆盖视频号相关能力后，`channel-video` 与 `openChannelsActivity` 才能在正式版使用。
