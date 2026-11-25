const api = require('../../utils/request')
const format = require('../../utils/format')

const PAGE_SIZE = 30

Page({
  data: { balance: '0', items: [], total: 0, page: 0, hasMore: true, loading: false, error: '' },

  onLoad() {
    this.reload()
  },

  onPullDownRefresh() {
    this.reload().then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    this.loadMore()
  },

  reload() {
    this.setData({ items: [], page: 0, hasMore: true, total: 0 })
    return this.loadMore()
  },

  loadMore() {
    if (this.data.loading || !this.data.hasMore) return Promise.resolve()
    const page = this.data.page + 1
    this.setData({ loading: true })
    return api
      .get('/flowers/ledger', { page, page_size: PAGE_SIZE }, { auth: true })
      .then((res) => {
        const items = this.data.items.concat(
          res.items.map((it) =>
            Object.assign({}, it, {
              time: format.datetime(it.created_at),
              deltaText: (it.delta > 0 ? '+' : '') + it.delta
            })
          )
        )
        this.setData({
          balance: format.number(res.balance),
          items,
          total: res.total,
          page,
          hasMore: items.length < res.total,
          loading: false,
          error: ''
        })
      })
      .catch((err) => this.setData({ loading: false, error: err.message }))
  }
})
