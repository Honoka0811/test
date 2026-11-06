// サムネイル(字幕なしのタイトル画面)を PNG で書き出す: node thumbnail.js [出力パス]
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const out = process.argv[2] || path.join(__dirname, 'output', 'thumbnail.png');
  const timing = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timing.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.addInitScript((tm) => { window.TIMING = tm; window.__capture = true; window.__thumb = true; }, timing);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const d = await page.evaluate(() => { window.render(4.0); return document.getElementById('c').toDataURL('image/png'); });
  fs.writeFileSync(out, Buffer.from(d.split(',')[1], 'base64'));
  await browser.close(); console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
