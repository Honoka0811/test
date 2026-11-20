// タイトルカードを字幕なしで撮影してサムネイルにする: node thumbnail.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'render.html') + '?capture');
  await p.evaluate(() => window.fontsReady);
  await p.evaluate(() => { window.NOSUB = true; window.render(3.0); });
  await p.screenshot({ path: path.join(__dirname, 'output', 'thumbnail.png') });
  await b.close();
})();
