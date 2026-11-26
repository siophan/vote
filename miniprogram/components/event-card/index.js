const icons = require('../../utils/icons')
const format = require('../../utils/format')

Component({
  options: { addGlobalClass: true },
  properties: {
    event: { type: Object, value: {} },
    // waterfall：首页双列瀑布流；catalog：赛事中心 16:9 大卡
    variant: { type: String, value: 'catalog' },
    thumbHeight: { type: Number, value: 300 }
  },
  data: { giftIcon: icons.gift.orange, participants: '0', flowers: '0' },
  observers: {
    event(event) {
      if (!event) return
      this.setData({
        participants: format.number(event.participant_count),
        flowers: format.number(event.flower_count)
      })
    }
  },
  methods: {
    open() {
      const id = this.data.event && this.data.event.id
      if (id) wx.navigateTo({ url: `/pages/event-detail/event-detail?id=${id}` })
    },
    // 已报名：直接去投稿并预选该赛事；未报名：进详情页报名
    onJoin() {
      const event = this.data.event
      if (!event || !event.id) return
      if (!event.enrolled) return this.open()
      wx.navigateTo({ url: `/pages/submit/submit?event_id=${event.id}` })
    }
  }
})
