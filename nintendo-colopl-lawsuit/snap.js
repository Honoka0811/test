// 指定時刻のフレームを PNG に書き出す(確認用): node snap.js out.png t1 t2 ...
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const timing = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timing.json'), 'utf8'));
  const outdir = process.argv[2]; const times = process.argv.slice(3).map(Number);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.addInitScript((tm) => { window.TIMING = tm; window.__capture = true; }, timing);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  for (const t of times) {
    const d = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    fs.writeFileSync(path.join(outdir, `f_${t.toFixed(1)}.png`), Buffer.from(d.split(',')[1], 'base64'));
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
