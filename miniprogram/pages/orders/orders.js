const api = require('../../utils/request')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

const TONES = { pending_shipment: 'wait', shipped: 'ok', completed: 'ok', cancelled: '' }

Page({
  data: { orders: [], loading: true, error: '', cancellingId: null },

  onShow() {
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  load() {
    return api
      .get('/me/orders', null, { auth: true })
      .then((orders) =>
        this.setData({
          loading: false,
          error: '',
          orders: orders.map((o) =>
            Object.assign({}, o, {
              tone: TONES[o.status] || '',
              created: format.datetime(o.created_at),
              totalText: format.number(o.total_price)
            })
          )
        })
      )
      .catch((err) => this.setData({ loading: false, error: err.message }))
  },

  cancel(e) {
    const id = e.currentTarget.dataset.id
    ui.confirm('取消订单', '取消后小红花会退回你的账户。', '确认取消').then((ok) => {
      if (!ok) return
      this.setData({ cancellingId: id })
      api
        .post(`/orders/${id}/cancel`)
        .then(() => {
          this.setData({ cancellingId: null })
          ui.toast('订单已取消，小红花已退回')
          this.load()
        })
        .catch((err) => {
          this.setData({ cancellingId: null })
          ui.errorToast(err)
        })
    })
  },

  copyTracking(e) {
    wx.setClipboardData({ data: e.currentTarget.dataset.no })
  },

  goMall() {
    wx.switchTab({ url: '/pages/mall/mall' })
  }
})
