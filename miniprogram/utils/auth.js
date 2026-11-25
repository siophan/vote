const config = require('../config')

const TOKEN_KEY = 'lhl_token'
let loginPromise = null

function getToken() {
  try {
    return wx.getStorageSync(TOKEN_KEY) || ''
  } catch (e) {
    return ''
  }
}

function clearToken() {
  try {
    wx.removeStorageSync(TOKEN_KEY)
  } catch (e) {}
}

function setUser(user) {
  const app = getApp()
  if (app && app.globalData) app.globalData.user = user
}

function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => (res.code ? resolve(res.code) : reject(new Error('微信登录失败'))),
      fail: () => reject(new Error('微信登录失败'))
    })
  })
}

function exchange(code) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: config.API_BASE + '/auth/login',
      method: 'POST',
      data: { code },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.token) {
          resolve(res.data)
        } else {
          reject(new Error((res.data && res.data.detail) || '登录失败，请稍后再试'))
        }
      },
      fail: () => reject(new Error('网络连接失败，请稍后再试'))
    })
  })
}

// 并发调用只会触发一次真正的登录
function login() {
  if (loginPromise) return loginPromise
  loginPromise = wxLogin()
    .then(exchange)
    .then((data) => {
      wx.setStorageSync(TOKEN_KEY, data.token)
      setUser(data.user)
      return data
    })
  const done = () => {
    loginPromise = null
  }
  loginPromise.then(done, done)
  return loginPromise
}

function ensureLogin() {
  return getToken() ? Promise.resolve() : login()
}

module.exports = { getToken, clearToken, login, ensureLogin, setUser }
