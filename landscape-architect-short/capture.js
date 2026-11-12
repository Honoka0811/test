// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(無音)にエンコードする
// 使い方: node capture.js [出力パス]   /   node capture.js --stills 出力dir   (各シーンの静止画だけ書き出す)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const stills = process.argv[2] === '--stills' ? process.argv[3] : null;
  const out = (!stills && process.argv[2]) || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(stills || path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const { FPS, DURATION, scenes } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION, scenes: window.TIMINGS.scenes }));
  const stage = page.locator('#stage');

  if (stills) {
    for (const [i, s] of scenes.entries()) {
      await page.evaluate((t) => window.render(t), s.start + s.dur - 0.5);
      await page.evaluate(() => document.fonts.ready);
      await stage.screenshot({ path: path.join(stills, `scene${i}_${s.id}.png`) });
    }
    await browser.close();
    return;
  }

  const total = Math.ceil(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', (d) => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    await page.evaluate((t) => window.render(t), i / FPS);
    const buf = await stage.screenshot({ type: 'jpeg', quality: 96 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch((e) => { console.error(e); process.exit(1); });
