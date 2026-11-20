// 使い方: node render.js <出力フレームディレクトリ> [fps]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const out = process.argv[2] || 'frames';
  const fps = +(process.argv[3] || 30);
  const only = process.argv[4]; // 指定時はその秒数の1枚だけ書き出す（確認用）
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.resolve(__dirname, 'video.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  const dur = await page.evaluate(() => window.DURATION);
  const times = only ? only.split(',').map(Number) : [...Array(Math.round(dur * fps)).keys()].map(i => i / fps);
  for (let i = 0; i < times.length; i++) {
    await page.evaluate(t => window.render(t), times[i]);
    const name = only ? `check_${times[i]}.png` : `f${String(i).padStart(5, '0')}.jpg`;
    await page.screenshot({ path: path.join(out, name), type: only ? 'png' : 'jpeg', quality: only ? undefined : 92 });
    if (!only && i % 150 === 0) console.log(`${i}/${times.length}`);
  }
  await browser.close();
})();
