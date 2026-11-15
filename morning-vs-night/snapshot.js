// 指定時刻のフレームを PNG で書き出す(確認用・サムネイル用)
// 使い方: node snapshot.js 出力ディレクトリ 1.5 8 20 ...
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const [dir, ...times] = process.argv.slice(2);
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error('pageerror', e));
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  for (const t of times) {
    const url = await page.evaluate(t => { window.render(+t); return document.getElementById('c').toDataURL('image/png'); }, t);
    fs.writeFileSync(path.join(dir, `f_${t}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close();
})();
