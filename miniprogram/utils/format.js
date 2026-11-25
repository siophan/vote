function number(value) {
  const n = Number(value || 0)
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function pad(n) {
  return n < 10 ? '0' + n : String(n)
}

// ISO8601 → 2026-11-26 14:03
function datetime(iso) {
  if (!iso) return ''
  // ISO8601 带 T 的格式在 iOS / Android 上都能直接解析；去掉微秒避免个别机型失败
  const d = new Date(String(iso).replace(/(\.\d{3})\d+/, '$1'))
  if (isNaN(d.getTime())) return String(iso).slice(0, 16).replace('T', ' ')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function date(iso) {
  return datetime(iso).slice(0, 10)
}

const SUBMISSION_STATUS = {
  pending: { text: '审核中', tone: 'wait' },
  approved: { text: '已通过', tone: 'ok' },
  rejected: { text: '未通过', tone: 'bad' }
}

module.exports = { number, datetime, date, SUBMISSION_STATUS }
