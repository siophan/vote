const config = require('../config')

const asset = (name) => config.ASSET_BASE + name

module.exports = {
  asset,
  hero: asset('hero-community-v2.webp'),
  logo: asset('logo-linghua-li.webp'),
  sprite: asset('icon-sprite.webp')
}
