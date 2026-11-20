// Renders scene.html frame by frame into frames/ (1080x1920 JPEG).
// usage: node render.js            -> all frames
//        node render.js 12.5 30.1  -> only preview stills at those times (preview/)
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TL = JSON.parse(fs.readFileSync(path.resolve(process.env.TIMELINE || path.join(__dirname, 'timeline.json')), 'utf8'));
const url = 'file://' + path.join(__dirname, TL.scene || 'scene.html');
const WORKERS = 4;

async function openPage(browser) {
  const ctx = await browser.newContext({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.goto(url);
  await page.evaluate(tl => window.init(tl), TL);
  return page;
}

(async () => {
  const browser = await chromium.launch();
  const stills = process.argv.slice(2).map(Number);
  if (stills.length) {
    fs.mkdirSync(path.join(__dirname, 'preview'), { recursive: true });
    const page = await openPage(browser);
    for (const t of stills) {
      await page.evaluate(t => window.render(t), t);
      await page.screenshot({ path: path.join(__dirname, 'preview', `t${t.toFixed(2)}.jpg`), type: 'jpeg', quality: 80 });
    }
  } else {
    const dir = path.join(__dirname, 'frames');
    fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
    const total = Math.round(TL.end * TL.fps);
    await Promise.all([...Array(WORKERS).keys()].map(async w => {
      const page = await openPage(browser);
      for (let i = w; i < total; i += WORKERS) {
        await page.evaluate(t => window.render(t), i / TL.fps);
        await page.screenshot({ path: path.join(dir, String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 95 });
      }
    }));
    console.log('frames:', total);
  }
  await browser.close();
})();
