const api = require('../../utils/request')
const icons = require('../../utils/icons')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

const WORKS_PAGE = 20

function workRow(w) {
  return Object.assign({}, w, { flowers: format.number(w.flower_count) })
}

Page({
  data: {
    id: null,
    event: null,
    stats: {},
    works: [],
    worksTotal: 0,
    worksPage: 1,
    worksLoading: false,
    enrolling: false,
    error: '',
    icons: { gift: icons.gift.orange, user: icons.user.olive, flower: icons.flower.orange }
  },

  onLoad(query) {
    this.setData({ id: Number(query.id) })
    this.load()
  },

  onShow() {
    // 从作品页送花回来，刷新数字
    if (this._shown) this.load()
    this._shown = true
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    this.loadMoreWorks()
  },

  load() {
    const id = this.data.id
    return Promise.all([
      api.get(`/events/${id}`, null, { auth: true }),
      api.get(`/events/${id}/submissions`, { page: 1, page_size: WORKS_PAGE })
    ])
      .then(([event, works]) => {
        wx.setNavigationBarTitle({ title: event.title })
        this.setData({
          event,
          error: '',
          stats: {
            participants: format.number(event.participant_count),
            flowers: format.number(event.flower_count)
          },
          works: works.items.map(workRow),
          worksTotal: works.total,
          worksPage: 1
        })
      })
      .catch((err) => {
        this.setData({ error: err.message })
        if (this.data.event) ui.errorToast(err)
      })
  },

  loadMoreWorks() {
    const { works, worksTotal, worksPage, worksLoading, id } = this.data
    if (worksLoading || works.length >= worksTotal) return
    this.setData({ worksLoading: true })
    api
      .get(`/events/${id}/submissions`, { page: worksPage + 1, page_size: WORKS_PAGE })
      .then((res) => {
        const seen = {}
        works.forEach((w) => (seen[w.id] = true))
        this.setData({
          works: works.concat(res.items.filter((w) => !seen[w.id]).map(workRow)),
          worksTotal: res.total,
          worksPage: worksPage + 1,
          worksLoading: false
        })
      })
      .catch((err) => {
        this.setData({ worksLoading: false })
        ui.errorToast(err)
      })
  },

  enroll() {
    if (this.data.enrolling) return
    this.setData({ enrolling: true })
    api
      .post(`/events/${this.data.id}/enroll`)
      .then((res) => {
        this.setData({
          'event.enrolled': true,
          'event.participant_count': res.participant_count,
          'stats.participants': format.number(res.participant_count),
          enrolling: false
        })
        const user = getApp().globalData.user
        if (user) user.flower_balance = res.flower_balance
        if (res.first_time) {
          wx.showModal({
            title: '报名成功',
            content: res.bonus
              ? `已获得 ${res.bonus} 朵小红花报名奖励。现在去提交你的视频号作品吧！`
              : '今天的报名奖励已经领满 3 次，明天报名还能得小红花。现在去提交你的视频号作品吧！',
            confirmText: '去投稿',
            cancelText: '稍后',
            confirmColor: '#d97945',
            success: (r) => r.confirm && this.goSubmit()
          })
        } else {
          ui.toast('你已经报名过这个赛事')
        }
      })
      .catch((err) => {
        this.setData({ enrolling: false })
        ui.errorToast(err)
      })
  },

  goSubmit() {
    getApp().globalData.submitEventId = this.data.id
    wx.switchTab({ url: '/pages/submit/submit' })
  },

  openWork(e) {
    wx.navigateTo({ url: `/pages/work/work?id=${e.currentTarget.dataset.id}` })
  },

  onShareAppMessage() {
    const event = this.data.event || {}
    return {
      title: `${event.title || '龄花里赛事'}｜${event.desc || '用一条视频参加身边的比赛'}`,
      path: `/pages/event-detail/event-detail?id=${this.data.id}`,
      imageUrl: event.cover_url
    }
  }
})
