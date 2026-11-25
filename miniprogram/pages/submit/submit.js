const api = require('../../utils/request')
const icons = require('../../utils/icons')
const ui = require('../../utils/ui')

function loadAllEvents() {
  // 后端单页最多 100 条，赛事目前 110 个
  const fetchPage = (page, acc) =>
    api.get('/events', { page, page_size: 100 }).then((res) => {
      const all = acc.concat(res.items)
      return all.length < res.total && res.items.length ? fetchPage(page + 1, all) : all
    })
  return fetchPage(1, [])
}

Page({
  data: {
    groups: [], // [{ name, events: [] }]
    columns: [[], []],
    pickerIndex: [0, 0],
    selected: null,
    title: '',
    description: '',
    videoUrl: '',
    agreed: false,
    submitting: false,
    linkError: '',
    loadError: '',
    icons: {
      film: icons.film.orange,
      chevron: icons.chevron.muted,
      info: icons.info.muted,
      check: icons.check.olive
    }
  },

  onLoad() {
    this.loadEvents()
  },

  onShow() {
    ui.syncTab(this, 2)
    this.applyPreselect()
  },

  loadEvents() {
    this.setData({ loadError: '' })
    return loadAllEvents()
      .then((events) => {
        const groups = []
        const byName = {}
        events.forEach((event) => {
          if (!byName[event.category]) {
            byName[event.category] = { name: event.category, events: [] }
            groups.push(byName[event.category])
          }
          byName[event.category].events.push(event)
        })
        this.setData({ groups })
        this.setColumns(0, 0)
        this.applyPreselect()
      })
      .catch((err) => this.setData({ loadError: err.message }))
  },

  applyPreselect() {
    const app = getApp()
    const id = app.globalData.submitEventId
    if (!id || !this.data.groups.length) return
    app.globalData.submitEventId = null
    this.data.groups.forEach((group, gi) => {
      group.events.forEach((event, ei) => {
        if (event.id === id) {
          this.setColumns(gi, ei)
          this.setData({ selected: event })
        }
      })
    })
  },

  setColumns(gi, ei) {
    const groups = this.data.groups
    if (!groups.length) return
    this.setData({
      columns: [groups.map((g) => g.name), groups[gi].events.map((e) => e.title)],
      pickerIndex: [gi, ei]
    })
  },

  onColumnChange(e) {
    const { column, value } = e.detail
    if (column === 0) this.setColumns(value, 0)
    else this.setData({ 'pickerIndex[1]': value })
  },

  onPick(e) {
    const [gi, ei] = e.detail.value
    const group = this.data.groups[gi]
    const event = group && group.events[ei || 0]
    if (event) this.setData({ selected: event })
  },

  onTitle(e) {
    this.setData({ title: e.detail.value })
  },
  onDesc(e) {
    this.setData({ description: e.detail.value })
  },
  onUrl(e) {
    this.setData({ videoUrl: e.detail.value.trim(), linkError: '' })
  },

  paste() {
    wx.getClipboardData({
      success: (res) => {
        // 视频号「复制链接」得到的通常是一段文字 + 链接，这里只取出链接
        const text = String(res.data || '')
        const match = text.match(/https?:\/\/[^\s，。]+/)
        const url = match ? match[0] : text.trim()
        this.setData({ videoUrl: url, linkError: url && !ui.isChannelsUrl(url) ? '这不像是视频号链接，请确认后再提交' : '' })
        if (!url) ui.toast('剪贴板是空的')
      }
    })
  },

  goWorks() {
    wx.navigateTo({ url: '/pages/works/works' })
  },

  toggleAgree() {
    this.setData({ agreed: !this.data.agreed })
  },

  submit() {
    const { selected, title, description, videoUrl, agreed, submitting } = this.data
    if (submitting) return
    if (!selected) return ui.toast('请先选择要参加的赛事')
    if (!title.trim()) return ui.toast('请给作品起个标题')
    if (!ui.isChannelsUrl(videoUrl)) {
      this.setData({ linkError: '请粘贴视频号视频链接（weixin.qq.com / channels.weixin.qq.com）' })
      return
    }
    if (!agreed) return ui.toast('请先确认作品发布权')
    this.setData({ submitting: true })
    api
      .post('/submissions', { event_id: selected.id, title: title.trim(), description: description.trim(), video_url: videoUrl })
      .then(() => {
        this.setData({ submitting: false, title: '', description: '', videoUrl: '', agreed: false })
        wx.showModal({
          title: '投稿成功',
          content: '作品已进入审核，通过后会获得 50 朵小红花，并出现在赛事作品榜里。审核结果可在本页右上角「我的作品」查看。',
          confirmText: '看我的作品',
          cancelText: '继续投稿',
          confirmColor: '#d97945',
          success: (r) => r.confirm && wx.navigateTo({ url: '/pages/works/works' })
        })
      })
      .catch((err) => {
        this.setData({ submitting: false })
        // 链接相关的错误（格式不对、重复投稿）显示在链接输入框下方，比 toast 更容易看清
        if (err.statusCode === 400 && /视频/.test(err.message)) this.setData({ linkError: err.message })
        else ui.errorToast(err)
      })
  }
})
