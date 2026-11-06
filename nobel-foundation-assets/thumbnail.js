// サムネイル(1080x1920)を render.html の描画関数で作る
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const out = process.argv[2] || path.join(__dirname, 'output', 'thumbnail.png');
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'render.html')); await p.evaluate(() => document.fonts.ready);
  await p.evaluate(() => window.thumbnail()); await p.locator('#c').screenshot({ path: out });
  await b.close(); console.log('wrote', out);
})();
