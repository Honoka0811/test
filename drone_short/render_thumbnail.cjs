// thumbnail.html を 1280x720（通常動画用）と 1080x1920（ショート用）で書き出す
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto('file://' + path.join(__dirname, 'thumbnail.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(__dirname, 'thumbnail_16x9.png') });

  await page.setViewportSize({ width: 1080, height: 1920 });
  await page.evaluate(() => { const w = document.getElementById('l'); w.className = 'wrap v'; });
  await page.screenshot({ path: path.join(__dirname, 'thumbnail_vertical.png') });
  await browser.close();
  console.log('thumbnails written');
})();
