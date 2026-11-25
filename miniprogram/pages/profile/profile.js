const api = require('../../utils/request')
const icons = require('../../utils/icons')
const ui = require('../../utils/ui')

Page({
  data: {
    avatarUrl: '',
    nickname: '',
    region: [],
    community: '',
    saving: false,
    uploading: false,
    icons: { user: icons.user.olive, chevron: icons.chevron.muted }
  },

  onLoad() {
    api
      .get('/me', null, { auth: true })
      .then((user) => {
        this.setData({
          avatarUrl: user.avatar_url || '',
          nickname: user.nickname || '',
          // 后端只存市、区，省份留空时 picker 也能正常显示
          region: user.city ? ['', user.city, user.district || ''] : [],
          community: user.community || ''
        })
      })
      .catch((err) => ui.errorToast(err))
  },

  onChooseAvatar(e) {
    const tempPath = e.detail.avatarUrl
    if (!tempPath) return
    this.setData({ uploading: true, avatarUrl: tempPath })
    api
      .upload('/me/avatar', tempPath)
      .then((res) => this.setData({ avatarUrl: res.avatar_url, uploading: false }))
      .catch((err) => {
        this.setData({ uploading: false })
        ui.errorToast(err)
      })
  },

  onNickname(e) {
    this.setData({ nickname: e.detail.value })
  },

  onRegion(e) {
    this.setData({ region: e.detail.value })
  },

  onCommunity(e) {
    this.setData({ community: e.detail.value })
  },

  save() {
    const { nickname, region, community, avatarUrl, uploading, saving } = this.data
    if (saving) return
    if (uploading) return ui.toast('头像还在上传，请稍等')
    const name = nickname.trim()
    if (!name) return ui.toast('请填写昵称')
    const body = { nickname: name, community: community.trim() }
    if (region.length) {
      body.city = region[1] || ''
      body.district = region[2] || ''
    }
    if (/^https?:\/\//.test(avatarUrl)) body.avatar_url = avatarUrl
    this.setData({ saving: true })
    api
      .patch('/me', body)
      .then((user) => {
        getApp().globalData.user = user
        this.setData({ saving: false })
        ui.toast('资料已保存')
        setTimeout(() => wx.navigateBack(), 600)
      })
      .catch((err) => {
        this.setData({ saving: false })
        ui.errorToast(err)
      })
  }
})
