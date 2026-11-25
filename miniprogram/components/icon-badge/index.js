const assets = require('../../utils/assets')

// icon-sprite.webp：5 列 × 2 行，每格约 355×443
const POSITIONS = {
  microphone: [0, 0],
  leaf: [1, 0],
  craft: [2, 0],
  heart: [3, 0],
  book: [4, 0],
  compass: [0, 1],
  food: [1, 1],
  handshake: [2, 1],
  phone: [3, 1],
  sparkle: [4, 1],
  medal: [4, 1]
}

Component({
  properties: {
    iconKey: { type: String, value: 'sparkle' },
    size: { type: Number, value: 68 } // rpx，徽章宽度
  },
  data: { sprite: assets.sprite, col: 4, row: 1 },
  observers: {
    iconKey(key) {
      const pos = POSITIONS[key] || POSITIONS.sparkle
      this.setData({ col: pos[0], row: pos[1] })
    }
  }
})
