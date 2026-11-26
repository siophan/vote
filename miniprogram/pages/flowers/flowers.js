const api = require('../../utils/request')
const icons = require('../../utils/icons')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

function levelProgress(user) {
  if (!user) return { percent: 0, text: '' }
  const next = user.next_level_value
  if (!next) return { percent: 100, text: '已达到最高等级' }
  const percent = Math.max(4, Math.min(100, Math.round((user.growth_value / next) * 100)))
  return { percent, text: `距离「${user.next_level_name}」还差 ${next - user.growth_value} 成长值` }
}

Page({
  data: {
    user: null,
    balance: '0',
    progress: { percent: 0, text: '' },
    scope: 'all', // all | city
    rankings: [],
    rankLoading: true,
    sendingId: null,
    icons: {
      bag: icons.bag.orange,
      handshake: icons.handshake.orange,
      flower: icons.flower.orange,
      medal: icons.medal.orange,
      user: icons.user.olive
    }
  },

  onShow() {
    ui.syncTab(this, 2)
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  load() {
    return Promise.all([this.loadUser(), this.loadRankings()])
  },

  loadUser() {
    return api
      .get('/me', null, { auth: true })
      .then((user) => {
        getApp().globalData.user = user
        this.setData({ user, balance: format.number(user.flower_balance), progress: levelProgress(user) })
      })
      .catch((err) => ui.errorToast(err))
  },

  loadRankings() {
    const user = this.data.user || getApp().globalData.user
    const city = this.data.scope === 'city' && user ? user.city : ''
    this.setData({ rankLoading: true })
    return api
      .get('/rankings', { city, limit: 20 })
      .then((rankings) =>
        this.setData({
          rankLoading: false,
          rankings: rankings.map((r) => Object.assign({}, r, { flowers: format.number(r.flower_count) }))
        })
      )
      .catch(() => this.setData({ rankLoading: false, rankings: [] }))
  },

  setScope(e) {
    const scope = e.currentTarget.dataset.scope
    if (scope === this.data.scope) return
    const user = this.data.user
    if (scope === 'city' && !(user && user.city)) {
      ui.confirm('还没设置所在城市', '设置城市后就能看到同城的作品榜单。', '去设置').then((ok) => {
        if (ok) wx.navigateTo({ url: '/pages/profile/profile' })
      })
      return
    }
    this.setData({ scope })
    this.loadRankings()
  },

  sendOne(e) {
    const id = e.currentTarget.dataset.id
    if (this.data.sendingId) return
    this.setData({ sendingId: id })
    api
      .post(`/submissions/${id}/flowers`, { count: 1 })
      .then((res) => {
        const rankings = this.data.rankings.map((r) =>
          r.submission_id === id ? Object.assign({}, r, { flower_count: res.submission_flower_count, flowers: format.number(res.submission_flower_count) }) : r
        )
        this.setData({ sendingId: null, rankings, balance: format.number(res.flower_balance), 'user.flower_balance': res.flower_balance })
        ui.toast('已送出 1 朵小红花，感谢你的支持')
      })
      .catch((err) => {
        this.setData({ sendingId: null })
        ui.errorToast(err)
      })
  },

  openWork(e) {
    wx.navigateTo({ url: `/pages/work/work?id=${e.currentTarget.dataset.id}` })
  },

  goLedger() {
    wx.navigateTo({ url: '/pages/ledger/ledger' })
  },
  goMall() {
    wx.switchTab({ url: '/pages/mall/mall' })
  },
  goCharity() {
    getApp().globalData.mallCategory = '公益专区'
    wx.switchTab({ url: '/pages/mall/mall' })
  },
  goRanking() {
    wx.pageScrollTo({ selector: '#ranking', offsetTop: -12, duration: 260 })
  },
  goMine() {
    wx.switchTab({ url: '/pages/mine/mine' })
  }
})
