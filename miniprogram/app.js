const auth = require('./utils/auth')

App({
  globalData: {
    user: null,
    // 从赛事详情跳到「投稿」tab 时预选的赛事（switchTab 不能带参数）
    submitEventId: null,
    // 从小红花页跳到商城时预选的分类
    mallCategory: null
  },

  onLaunch() {
    // wx.login 是静默登录，不打扰用户；失败时各页面请求会再次尝试
    auth.ensureLogin().catch(() => {})
  }
})
