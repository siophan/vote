const api = require('../../utils/request')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

const CATEGORIES = ['全部', '暖心日用', '食养好物', '公益专区']

function chooseAddress() {
  return new Promise((resolve, reject) => {
    wx.chooseAddress({
      success: (a) =>
        resolve({
          name: a.userName,
          phone: a.telNumber,
          province: a.provinceName,
          city: a.cityName,
          district: a.countyName,
          detail: a.detailInfo
        }),
      fail: (err) => {
        const cancelled = err && /cancel/.test(err.errMsg || '')
        reject(new Error(cancelled ? '' : '需要收货地址才能兑换实物商品'))
      }
    })
  })
}

Page({
  data: {
    categories: CATEGORIES,
    category: '全部',
    products: [],
    balance: 0,
    balanceText: '0',
    loading: true,
    error: '',
    redeemingId: null
  },

  onShow() {
    ui.syncTab(this, 4)
    const app = getApp()
    if (app.globalData.mallCategory) {
      this.setData({ category: app.globalData.mallCategory })
      app.globalData.mallCategory = null
    }
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  load() {
    return Promise.all([this.loadProducts(), this.loadBalance()])
  },

  loadBalance() {
    return api
      .get('/me', null, { auth: true })
      .then((user) => {
        getApp().globalData.user = user
        this.setBalance(user.flower_balance)
      })
      .catch(() => {})
  },

  setBalance(value) {
    this.setData({ balance: value, balanceText: format.number(value) })
  },

  loadProducts() {
    const category = this.data.category
    return api
      .get('/products', { category: category === '全部' ? '' : category })
      .then((products) => {
        if (category !== this.data.category) return
        this.setData({
          loading: false,
          error: '',
          products: products.map((p) => Object.assign({}, p, { priceText: format.number(p.price) }))
        })
      })
      .catch((err) => this.setData({ loading: false, error: err.message }))
  },

  setCategory(e) {
    const category = e.currentTarget.dataset.name
    if (category === this.data.category) return
    this.setData({ category, loading: true })
    this.loadProducts()
  },

  redeem(e) {
    const product = this.data.products[e.currentTarget.dataset.index]
    if (!product || this.data.redeemingId) return
    if (product.stock <= 0) return ui.toast('这件商品暂时兑完了')
    if (this.data.balance < product.price) return ui.toast('小红花余额不足，先去参加赛事吧')

    const isCharity = product.kind === 'charity'
    const action = isCharity ? '支持' : '兑换'
    ui.confirm(`${action}「${product.name}」`, `将使用 ${product.price} 朵小红花。${isCharity ? '支持后不可撤销。' : '下一步请选择收货地址，发货前可在订单里取消。'}`, `确认${action}`)
      .then((ok) => {
        if (!ok) throw new Error('')
        return isCharity ? null : chooseAddress()
      })
      .then((address) => {
        this.setData({ redeemingId: product.id })
        const body = { product_id: product.id, quantity: 1 }
        if (address) body.address = address
        return api.post('/orders', body)
      })
      .then((order) => {
        this.setData({ redeemingId: null })
        this.load()
        wx.showModal({
          title: isCharity ? '感谢你的支持' : '兑换成功',
          content: isCharity ? `「${product.name}」已记录到你的公益订单。` : `「${product.name}」${order.status_text}，可在「我的订单」查看进度。`,
          confirmText: '查看订单',
          cancelText: '继续逛逛',
          confirmColor: '#d97945',
          success: (r) => r.confirm && wx.navigateTo({ url: '/pages/orders/orders' })
        })
      })
      .catch((err) => {
        this.setData({ redeemingId: null })
        if (err && err.message) ui.errorToast(err)
      })
  },

  goOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' })
  }
})
