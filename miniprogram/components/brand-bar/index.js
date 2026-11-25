const assets = require('../../utils/assets')
const icons = require('../../utils/icons')

Component({
  options: { addGlobalClass: true },
  properties: {
    avatarUrl: { type: String, value: '' }
  },
  data: {
    logo: assets.logo,
    userIcon: icons.user.olive,
    statusBar: 20,
    navHeight: 44,
    rightGap: 100
  },
  lifetimes: {
    attached() {
      const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
      const statusBar = win.statusBarHeight || 20
      let navHeight = 44
      let rightGap = 100
      try {
        const capsule = wx.getMenuButtonBoundingClientRect()
        navHeight = (capsule.top - statusBar) * 2 + capsule.height
        rightGap = win.windowWidth - capsule.left + 8
      } catch (e) {}
      this.setData({ statusBar, navHeight, rightGap })
    }
  },
  methods: {
    onMine() {
      wx.navigateTo({ url: '/pages/mine/mine' })
    }
  }
})
