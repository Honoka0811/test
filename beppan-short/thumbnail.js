// thumbnail.html を縦(1080×1920)と横(1280×720)で撮影して JPG にする
// 使い方: node thumbnail.js
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  for (const [v, w, h] of [['tall', 1080, 1920], ['wide', 1280, 720]]) {
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await page.goto('file://' + path.join(__dirname, 'thumbnail.html') + '?v=' + v);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const png = path.join(__dirname, 'output', `thumbnail_${v}.png`);
    await page.locator('#card').screenshot({ path: png });
    const jpg = png.replace(/\.png$/, '.jpg');
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', png, '-q:v', '2', jpg]);
    require('fs').unlinkSync(png);
    console.log('wrote', jpg);
    await page.close();
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
