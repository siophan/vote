function toast(title) {
  wx.showToast({ title: String(title || ''), icon: 'none', duration: 2300 })
}

function errorToast(err) {
  toast((err && err.message) || '出了点问题，请稍后再试')
}

function confirm(title, content, confirmText = '确定') {
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmText,
      confirmColor: '#d97945',
      cancelColor: '#78685b',
      success: (res) => resolve(!!res.confirm),
      fail: () => resolve(false)
    })
  })
}

// 与后端一致的视频号链接校验，提前给出友好提示
function isChannelsUrl(value) {
  const match = /^https:\/\/([^/?#:]+)(?::\d+)?([/?#].*)?$/i.exec(String(value || '').trim())
  if (!match) return false
  const host = match[1].toLowerCase()
  return host === 'weixin.qq.com' || /\.weixin\.qq\.com$/.test(host) || host === 'finder.video.qq.com'
}

// tab 页 onShow 时同步自定义 tabBar 高亮
function syncTab(page, index) {
  if (typeof page.getTabBar === 'function' && page.getTabBar()) {
    page.getTabBar().setData({ selected: index })
  }
}

module.exports = { toast, errorToast, confirm, isChannelsUrl, syncTab }
