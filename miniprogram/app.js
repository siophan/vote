const auth = require('./utils/auth')

App({
  globalData: {
    user: null,
    // 从小红花页跳到商城时预选的分类
    mallCategory: null
  },

  onLaunch() {
    // wx.login 是静默登录，不打扰用户；失败时各页面请求会再次尝试
    auth.ensureLogin().catch(() => {})
  }
})
