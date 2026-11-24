// 使い方: node render.js [preview 秒,秒,...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const { spawn } = require('child_process');
(async () => {
  const TL = JSON.parse(fs.readFileSync('build/timeline.json'));
  const FPS = 30;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(tl => { window.TL = tl; }, TL);
  await page.goto('file://' + path.resolve('scene.html'));
  await page.evaluate(() => document.fonts.ready);
  const preview = process.argv[2];
  if (preview) {
    for (const s of preview.split(',')) {
      await page.evaluate(t => render(t), +s);
      await page.screenshot({ path: `build/prev_${s}.png` });
    }
    await browser.close(); return;
  }
  const n = Math.ceil(TL.total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', 'build/mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', 'provider_ranking_short.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => render(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.error(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
})();
