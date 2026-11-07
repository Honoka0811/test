// 指定した時刻のフレームを PNG に書き出す(確認用)
// 使い方: node preview.js 出力ディレクトリ t1 t2 ...
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [dir, ...ts] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => { await Promise.all(['NotoBlack', 'NotoBold', 'Dela'].map(f => document.fonts.load(`100px "${f}"`, 'あA1'))); });
  for (const t of ts) {
    const url = await page.evaluate(t => { window.render(+t); return document.getElementById('c').toDataURL('image/png'); }, t);
    require('fs').writeFileSync(path.join(dir, `f_${(+t).toFixed(2).padStart(6, '0')}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  if (errs.length) console.log('ERRORS:', errs);
  await browser.close();
})();
