// 运行环境配置。开发期指向本机后端；上线前改成 https 域名并在小程序后台配置 request 合法域名。
const ENV = {
  develop: {
    API_BASE: 'http://127.0.0.1:8001/api/v1',
    ASSET_BASE: 'http://127.0.0.1:8001/static/assets/'
  },
  trial: {
    API_BASE: 'https://api.example.com/api/v1',
    ASSET_BASE: 'https://cdn.example.com/linghuali/'
  },
  release: {
    API_BASE: 'https://api.example.com/api/v1',
    ASSET_BASE: 'https://cdn.example.com/linghuali/'
  }
}

let envVersion = 'develop'
try {
  envVersion = wx.getAccountInfoSync().miniProgram.envVersion || 'develop'
} catch (e) {}

module.exports = ENV[envVersion] || ENV.develop
