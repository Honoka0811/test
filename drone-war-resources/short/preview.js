// 指定時刻のフレームを PNG に書き出す(レイアウト確認用): node preview.js t1 t2 ...
const { chromium } = require('playwright');
const path = require('path'); const fs = require('fs');
(async () => {
  const times = process.argv.slice(2).map(Number);
  const timing = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timing.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate((tm) => window.setTiming(tm), timing);
  fs.mkdirSync(path.join(__dirname, 'output', 'preview'), { recursive: true });
  for (const t of times) {
    const d = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.85); }, t);
    fs.writeFileSync(path.join(__dirname, 'output', 'preview', `f_${t}.jpg`), Buffer.from(d.split(',')[1], 'base64'));
  }
  const th = await page.evaluate(() => { window.renderThumbnail(); return document.getElementById('c').toDataURL('image/jpeg', 0.85); });
  fs.writeFileSync(path.join(__dirname, 'output', 'preview', 'thumb.jpg'), Buffer.from(th.split(',')[1], 'base64'));
  await browser.close();
})();
