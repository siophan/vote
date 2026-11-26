const api = require('../../utils/request')
const assets = require('../../utils/assets')
const icons = require('../../utils/icons')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

// 原型瀑布流里三种封面高度交替
const THUMB_HEIGHTS = [284, 376, 316]

Page({
  data: {
    hero: assets.hero,
    left: [],
    right: [],
    rewards: [],
    loading: true,
    error: '',
    icons: {
      upload: icons.upload.orange,
      flower: icons.flower.orange,
      flowerSmall: icons.flower.orange
    }
  },

  onLoad() {
    this.load()
  },

  onShow() {
    ui.syncTab(this, 0)
    // 预取当前用户，供小红花等页面复用
    api
      .get('/me', null, { auth: true })
      .then((user) => {
        getApp().globalData.user = user
      })
      .catch(() => {})
    // 从详情页报名后回来，刷新卡片上的「已报名」
    if (this._loadedOnce) this.load()
    this._loadedOnce = true
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  load() {
    this.setData({ error: '' })
    return Promise.all([
      api.get('/events', { featured: 1 }, { auth: true }),
      api.get('/products', { featured: 1 })
    ])
      .then(([events, products]) => {
        const items = (events.items || events).map((event, index) => Object.assign({}, event, { thumbHeight: THUMB_HEIGHTS[index % 3] }))
        this.setData({
          left: items.filter((_, i) => i % 2 === 0),
          right: items.filter((_, i) => i % 2 === 1),
          rewards: products.map((p) => Object.assign({}, p, { priceText: format.number(p.price) })),
          loading: false
        })
      })
      .catch((err) => this.setData({ loading: false, error: err.message }))
  },

  goEvents() {
    wx.switchTab({ url: '/pages/events/events' })
  },
  goSubmit() {
    wx.navigateTo({ url: '/pages/submit/submit' })
  },
  goFlowers() {
    wx.switchTab({ url: '/pages/flowers/flowers' })
  },
  goMall() {
    wx.switchTab({ url: '/pages/mall/mall' })
  },

  onShareAppMessage() {
    return { title: '龄花里｜用一条视频参加身边的比赛', path: '/pages/home/home' }
  },
  onShareTimeline() {
    return { title: '龄花里｜银龄花开，相聚龄花里' }
  }
})
