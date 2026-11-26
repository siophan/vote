const api = require('../../utils/request')
const assets = require('../../utils/assets')
const ui = require('../../utils/ui')

const PAGE_SIZE = 20

// 视频号精选入口：内容方向参考，外链在小程序内不能直接打开，提供复制
const SHOWCASE = [
  { title: '银龄达人秀 · 才艺与生活记录', desc: '适合才艺开放麦、家庭故事和生活方式投稿。', source: '微信派 · 视频号活动', cover: 'category-talent.webp', url: 'https://huacheng.gz-cmc.com/pages/2021/10/15/ee296435e0a24b989e3acc2bebef145e.html' },
  { title: '太极教学与银龄健身', desc: '适合太极、八段锦、健步走和健康生活季。', source: '中国老年人才网 · 视频号案例', cover: 'category-health.webp', url: 'https://www.zglnrc.org.cn/xqws/6333.html' },
  { title: '福寿银龄 · 团队舞蹈专场', desc: '适合广场舞编舞、团队合拍和城市赛。', source: '山东广电 · 福寿银龄', cover: 'category-talent.webp', url: 'https://news.iqilu.com/shandong/shandonggedi/20250915/5850855.shtml' },
  { title: '银龄慢旅行 · 同城路线记录', desc: '适合公园四季摄影、家乡风物和同城慢旅行。', source: '龄花里 · 主题灵感', cover: 'category-travel.webp', category: '旅行' },
  { title: '家常食养与厨房记忆', desc: '适合家常菜一招、节气食养和家庭厨房记忆。', source: '国家老年大学 · 视频号课程', cover: 'category-food.webp', url: 'https://lndx.edu.cn/newsInfo/notice/89_344.html' },
  { title: '传统手艺与非遗一分钟', desc: '适合木作、编织、剪纸、书法和非遗展示。', source: '龄花里 · 手作赛事方向', cover: 'category-craft.webp', category: '手作' }
].map((item) => Object.assign({}, item, { coverUrl: assets.asset(item.cover) }))

Page({
  data: {
    summary: { event_count: 0, category_count: 0, geo_levels: 6 },
    categories: [],
    filter: '全部',
    events: [],
    total: 0,
    page: 0,
    hasMore: true,
    loading: false,
    error: '',
    showcase: SHOWCASE
  },

  onLoad() {
    this._seq = 0
    this.loadMeta()
    this.reload()
  },

  onShow() {
    ui.syncTab(this, 1)
    // 从详情页报名回来后，刷新「已报名」状态
    if (this._loadedOnce) this.refreshEnrolled()
    this._loadedOnce = true
  },

  onPullDownRefresh() {
    Promise.all([this.loadMeta(), this.reload()]).then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    this.loadMore()
  },

  loadMeta() {
    return Promise.all([api.get('/events/summary'), api.get('/categories')])
      .then(([summary, categories]) => this.setData({ summary, categories }))
      .catch(() => {})
  },

  reload() {
    // 作废进行中的请求：它回来时发现序号变了就丢弃结果，不会卡住 loading
    this._seq = (this._seq || 0) + 1
    this.setData({ events: [], page: 0, hasMore: true, total: 0, error: '', loading: false })
    return this.loadMore()
  },

  loadMore() {
    if (this.data.loading || !this.data.hasMore) return Promise.resolve()
    const seq = this._seq || 0
    const page = this.data.page + 1
    const filter = this.data.filter
    this.setData({ loading: true, error: '' })
    return api
      .get('/events', { category: filter === '全部' ? '' : filter, page, page_size: PAGE_SIZE }, { auth: true })
      .then((res) => {
        if (seq !== this._seq) return // 期间切换了分类或刷新，丢弃旧结果
        const events = this.data.events.concat(res.items)
        this.setData({ events, total: res.total, page, hasMore: events.length < res.total, loading: false })
      })
      .catch((err) => {
        if (seq !== this._seq) return
        this.setData({ loading: false, error: err.message + '，上拉或下拉可重试' })
      })
  },

  refreshEnrolled() {
    const count = this.data.events.length
    if (!count) return
    const seq = this._seq
    api
      .get('/events', { category: this.data.filter === '全部' ? '' : this.data.filter, page: 1, page_size: Math.min(100, count) }, { auth: true })
      .then((res) => {
        if (seq !== this._seq) return
        const byId = {}
        res.items.forEach((e) => (byId[e.id] = e))
        this.setData({ events: this.data.events.map((e) => byId[e.id] || e) })
      })
      .catch(() => {})
  },

  setFilter(e) {
    const filter = e.currentTarget.dataset.filter
    if (filter === this.data.filter) return
    this.setData({ filter })
    this.reload().then(() => {
      wx.pageScrollTo({ selector: '#catalog', offsetTop: -12, duration: 260 })
    })
  },

  goSubmit() {
    wx.navigateTo({ url: '/pages/submit/submit' })
  },

  onShowcase(e) {
    const item = this.data.showcase[e.currentTarget.dataset.index]
    if (item.url) {
      wx.setClipboardData({ data: item.url, success: () => ui.toast('来源链接已复制，可在浏览器中打开') })
    } else {
      this.setData({ filter: item.category })
      this.reload().then(() => wx.pageScrollTo({ selector: '#catalog', offsetTop: -12, duration: 260 }))
    }
  },

  onShareAppMessage() {
    return { title: '龄花里赛事中心｜15 大主题，总有一场适合你', path: '/pages/events/events' }
  }
})
