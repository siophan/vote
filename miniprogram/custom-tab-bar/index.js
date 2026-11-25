const icons = require('../utils/icons')

const TABS = [
  { path: '/pages/home/home', text: '发现', icon: 'home' },
  { path: '/pages/events/events', text: '赛事', icon: 'trophy' },
  { path: '/pages/submit/submit', text: '投稿', icon: 'upload' },
  { path: '/pages/flowers/flowers', text: '小红花', icon: 'flower' },
  { path: '/pages/mall/mall', text: '商城', icon: 'bag' }
]

Component({
  data: {
    selected: 0,
    tabs: TABS.map((tab) => ({
      path: tab.path,
      text: tab.text,
      iconOn: icons[tab.icon].olive,
      iconOff: icons[tab.icon].muted
    }))
  },
  methods: {
    onTap(e) {
      const index = e.currentTarget.dataset.index
      if (index === this.data.selected) return
      wx.switchTab({ url: this.data.tabs[index].path })
    }
  }
})
