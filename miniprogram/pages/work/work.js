const api = require('../../utils/request')
const icons = require('../../utils/icons')
const format = require('../../utils/format')
const ui = require('../../utils/ui')

const COUNTS = [1, 5, 10, 20]

// <channel-video> 只认带 "token/" 前缀的 feed-token（不带会报 fail 1416106）；后端已统一加前缀，这里再兜底
function withTokenPrefix(token) {
  if (!token) return null
  return token.indexOf('token/') === 0 ? token : 'token/' + token
}

Page({
  data: {
    id: null,
    work: null,
    isMine: false,
    status: null,
    created: '',
    flowers: '0',
    balance: 0,
    counts: COUNTS,
    count: 1,
    sending: false,
    error: '',
    videoError: '',
    showDebug: false,
    icons: {
      play: icons.play.cream,
      user: icons.user.olive,
      flower: icons.flower.orange,
      link: icons.link.olive
    }
  },

  onLoad(query) {
    let env = 'develop'
    try {
      env = wx.getAccountInfoSync().miniProgram.envVersion || 'develop'
    } catch (e) {}
    this.setData({ id: Number(query.id), showDebug: env !== 'release' })
    this.load()
  },

  load() {
    return Promise.all([api.get(`/submissions/${this.data.id}`, null, { auth: true }), api.get('/me', null, { auth: true })])
      .then(([work, me]) => {
        getApp().globalData.user = me
        work = Object.assign({}, work, { feed_token: withTokenPrefix(work.feed_token) })
        this.setData({
          work,
          isMine: work.author && work.author.id === me.id,
          status: format.SUBMISSION_STATUS[work.status] || null,
          created: format.date(work.created_at),
          flowers: format.number(work.flower_count),
          balance: me.flower_balance,
          error: ''
        })
        this.syncShareMenu(work)
      })
      .catch((err) => this.setData({ error: err.message }))
  },

  pickCount(e) {
    this.setData({ count: Number(e.currentTarget.dataset.count) })
  },


  // 小程序里打不开视频号网页链接，只能复制后到微信聊天里点开；分步说清楚
  copyLink() {
    wx.setClipboardData({
      data: this.data.work.video_url,
      success: () => {
        wx.hideToast()
        wx.showModal({
          title: '链接已复制',
          content: '1. 回到微信，打开「文件传输助手」或任意聊天\n2. 长按输入框，粘贴并发送\n3. 点一下发出的链接，就能看视频',
          showCancel: false,
          confirmText: '知道了',
          confirmColor: '#d97945'
        })
      }
    })
  },

  // 播放器报错就退回占位块；开发版 / 体验版把原因显示出来，方便核对 token
  onVideoError(e) {
    const detail = (e && e.detail) || {}
    console.error('[channel-video] error', detail)
    this.setData({
      'work.feed_token': null,
      videoError: detail.errMsg || detail.message || JSON.stringify(detail)
    })
  },

  send() {
    const { work, count, balance, sending, isMine } = this.data
    if (sending) return
    if (isMine) return ui.toast('不能给自己的作品送花哦')
    if (work.status !== 'approved') return ui.toast('作品审核通过后才能接受送花')
    if (balance < count) return ui.toast('小红花余额不足，去参加赛事赚一些吧')
    this.setData({ sending: true })
    api
      .post(`/submissions/${work.id}/flowers`, { count })
      .then((res) => {
        this.setData({
          sending: false,
          balance: res.flower_balance,
          'work.flower_count': res.submission_flower_count,
          flowers: format.number(res.submission_flower_count)
        })
        const user = getApp().globalData.user
        if (user) user.flower_balance = res.flower_balance
        ui.toast(`已送出 ${count} 朵小红花，感谢你的支持`)
      })
      .catch((err) => {
        this.setData({ sending: false })
        ui.errorToast(err)
      })
  },

  goEvent() {
    wx.navigateTo({ url: `/pages/event-detail/event-detail?id=${this.data.work.event_id}` })
  },

  syncShareMenu(work) {
    // 未通过审核的作品别人打不开，不让分享出去
    if (work.status === 'approved') wx.showShareMenu({ menus: ['shareAppMessage'] })
    else wx.hideShareMenu()
  },

  onShareAppMessage() {
    const work = this.data.work || {}
    if (work.status !== 'approved') {
      return { title: '龄花里｜用一条视频参加身边的比赛', path: '/pages/home/home' }
    }
    return { title: `${work.title || '龄花里作品'}｜来给我送朵小红花吧`, path: `/pages/work/work?id=${this.data.id}` }
  }
})
