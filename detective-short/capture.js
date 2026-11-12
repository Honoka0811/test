// render.html を1フレームずつ撮影する。
//   node capture.js            全フレームを output/frames/ へ
//   node capture.js 2.9 8.5    指定時刻(秒)だけ output/preview_*.png へ
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const FPS = 30, W = 1080, H = 1920, WORKERS = 4;
const out = path.join(__dirname, 'output');
const timeline = JSON.parse(fs.readFileSync(path.join(out, 'timeline.json'), 'utf8'));

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exit(1); });
  await page.addInitScript(tl => { window.TIMELINE = tl; }, timeline);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.READY);
  // 字幕や見出しで使う全グリフを先に読み込ませる
  await page.evaluate(async tl => {
    for (const t of [0, ...tl.lines.map(l => l.start + 0.3), tl.duration - 0.5]) window.renderAt(t);
    await document.fonts.ready;
    await new Promise(r => setTimeout(r, 300));
    await document.fonts.ready;
  }, timeline);
  return page;
}

(async () => {
  const browser = await chromium.launch();
  const times = process.argv.slice(2).map(Number);
  if (times.length) {
    const page = await openPage(browser);
    for (const t of times) {
      await page.evaluate(t => window.renderAt(t), t);
      await page.screenshot({ path: path.join(out, `preview_${t.toFixed(2)}.png`) });
    }
  } else {
    const dir = path.join(out, 'frames');
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    const total = Math.ceil(timeline.duration * FPS);
    let next = 0;
    await Promise.all(Array.from({ length: WORKERS }, async () => {
      const page = await openPage(browser);
      while (next < total) {
        const f = next++;
        await page.evaluate(t => window.renderAt(t), f / FPS);
        await page.screenshot({ path: path.join(dir, `f${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 95 });
        if (f % 200 === 0) console.log(`frame ${f}/${total}`);
      }
    }));
    console.log('frames', total);
  }
  await browser.close();
})();
