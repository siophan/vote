const api = require('../../utils/request')
const icons = require('../../utils/icons')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

Page({
  data: {
    user: null,
    balance: '0',
    percent: 0,
    enrollments: [],
    icons: {
      user: icons.user.olive,
      film: icons.film.orange,
      edit: icons.edit.orange,
      box: icons.box.orange,
      list: icons.list.orange,
      chevron: icons.chevron.muted
    }
  },

  onShow() {
    ui.syncTab(this, 4)
    Promise.all([api.get('/me', null, { auth: true }), api.get('/me/enrollments', null, { auth: true })])
      .then(([user, enrollments]) => {
        getApp().globalData.user = user
        const next = user.next_level_value
        this.setData({
          user,
          enrollments,
          balance: format.number(user.flower_balance),
          percent: next ? Math.max(4, Math.min(100, Math.round((user.growth_value / next) * 100))) : 100
        })
      })
      .catch((err) => ui.errorToast(err))
  },

  go(e) {
    wx.navigateTo({ url: e.currentTarget.dataset.url })
  },

  openEvent(e) {
    wx.navigateTo({ url: `/pages/event-detail/event-detail?id=${e.currentTarget.dataset.id}` })
  }
})
