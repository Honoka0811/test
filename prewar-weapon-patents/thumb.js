// render.html の指定時刻のフレームを PNG で書き出す(サムネイル / 確認用)
// 使い方: node thumb.js <秒> [出力パス]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const t = parseFloat(process.argv[2] || '4');
  const out = process.argv[3] || path.join(__dirname, 'output', 'thumbnail.png');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
  fs.writeFileSync(out, Buffer.from(dataUrl.split(',')[1], 'base64'));
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
