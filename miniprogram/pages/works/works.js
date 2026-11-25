const api = require('../../utils/request')
const format = require('../../utils/format')

Page({
  data: { works: [], loading: true, error: '' },

  onShow() {
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  load() {
    return api
      .get('/me/submissions', null, { auth: true })
      .then((works) =>
        this.setData({
          loading: false,
          error: '',
          works: works.map((w) =>
            Object.assign({}, w, {
              statusInfo: format.SUBMISSION_STATUS[w.status] || { text: w.status, tone: '' },
              created: format.datetime(w.created_at),
              flowers: format.number(w.flower_count)
            })
          )
        })
      )
      .catch((err) => this.setData({ loading: false, error: err.message }))
  },

  open(e) {
    wx.navigateTo({ url: `/pages/work/work?id=${e.currentTarget.dataset.id}` })
  },

  goSubmit() {
    wx.switchTab({ url: '/pages/submit/submit' })
  }
})
