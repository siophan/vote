const assets = require('../../utils/assets')

Component({
  options: { addGlobalClass: true },
  data: {
    logo: assets.logo,
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
  }
})
