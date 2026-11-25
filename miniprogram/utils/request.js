const config = require('../config')
const auth = require('./auth')

function detailOf(data) {
  if (!data) return ''
  const detail = data.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) return '提交的内容格式不正确'
  return ''
}

function cleanQuery(data) {
  if (!data) return data
  const out = {}
  Object.keys(data).forEach((key) => {
    const value = data[key]
    if (value !== undefined && value !== null && value !== '') out[key] = value
  })
  return out
}

function send(path, method, data) {
  return new Promise((resolve, reject) => {
    const header = { 'content-type': 'application/json' }
    const token = auth.getToken()
    if (token) header.Authorization = 'Bearer ' + token
    wx.request({
      url: config.API_BASE + path,
      method,
      data: method === 'GET' ? cleanQuery(data) : data,
      header,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(res.data)
        const err = new Error(detailOf(res.data) || `请求失败（${res.statusCode}）`)
        err.statusCode = res.statusCode
        reject(err)
      },
      fail: () => {
        const err = new Error('网络连接失败，请稍后再试')
        err.statusCode = 0
        reject(err)
      }
    })
  })
}

/**
 * request('/events', { data, method, auth })
 * auth: true 先确保登录；token 过期（401）时自动重新登录并重试一次。
 */
function request(path, options = {}) {
  const method = options.method || 'GET'
  const start = options.auth ? auth.ensureLogin() : Promise.resolve()
  return start
    .then(() => send(path, method, options.data))
    .catch((err) => {
      if (err.statusCode === 401 && options.retry !== false) {
        auth.clearToken()
        return auth.login().then(() => send(path, method, options.data))
      }
      throw err
    })
}

function upload(path, filePath, name = 'file') {
  return auth.ensureLogin().then(
    () =>
      new Promise((resolve, reject) => {
        wx.uploadFile({
          url: config.API_BASE + path,
          filePath,
          name,
          header: { Authorization: 'Bearer ' + auth.getToken() },
          success: (res) => {
            let data = {}
            try {
              data = JSON.parse(res.data)
            } catch (e) {}
            if (res.statusCode >= 200 && res.statusCode < 300) resolve(data)
            else reject(new Error(detailOf(data) || '上传失败'))
          },
          fail: () => reject(new Error('上传失败，请稍后再试'))
        })
      })
  )
}

module.exports = {
  request,
  upload,
  get: (path, data, opts = {}) => request(path, Object.assign({ data }, opts)),
  post: (path, data, opts = {}) => request(path, Object.assign({ method: 'POST', data, auth: true }, opts)),
  patch: (path, data, opts = {}) => request(path, Object.assign({ method: 'PATCH', data, auth: true }, opts))
}
