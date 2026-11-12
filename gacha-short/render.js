// index.html を 1 フレームずつシークして JPEG 連番に書き出す。
// 使い方: node render.js            … 全フレーム (build/frames/)
//         node render.js 1.5 9 20   … 指定秒のプレビュー静止画 (build/preview_*.png)
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const FPS = 30, WORKERS = 4;
const T = JSON.parse(fs.readFileSync(path.join(__dirname, 'build/timings.json'), 'utf8'));
const url = 'file://' + path.join(__dirname, 'index.html');

async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('pageerror', e); process.exit(1); });
  await page.addInitScript(t => { window.TIMINGS = t; }, T);
  await page.goto(url);
  await page.evaluate(() => window.ready);
  return page;
}

(async () => {
  const browser = await chromium.launch();
  const previews = process.argv.slice(2).map(Number);
  if (previews.length) {
    const page = await open(browser);
    for (const t of previews) {
      await page.evaluate(t => window.seek(t), t);
      await page.screenshot({ path: path.join(__dirname, `build/preview_${t.toFixed(1)}.png`) });
    }
  } else {
    const dir = path.join(__dirname, 'build/frames');
    fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const total = Math.ceil(T.total * FPS);
    let next = 0;
    await Promise.all(Array.from({ length: WORKERS }, async () => {
      const page = await open(browser);
      while (next < total) {
        const f = next++;
        await page.evaluate(t => window.seek(t), f / FPS);
        await page.screenshot({ path: path.join(dir, `f${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 95 });
        if (f % 150 === 0) console.log(`frame ${f}/${total}`);
      }
    }));
  }
  await browser.close();
})();
