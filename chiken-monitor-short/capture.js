// render.html を 1 フレームずつ撮影し、ffmpeg で音声(output/mix.wav)と合わせて mp4 にする
// 使い方: node capture.js [出力パス]      静止画の確認: node capture.js --stills 3,10,17
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const WORKERS = 4;
(async () => {
  const outDir = path.join(__dirname, 'output');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const pages = [];
  for (let i = 0; i < WORKERS; i++) {
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    await page.goto('file://' + path.join(__dirname, 'render.html'));
    await page.evaluate(() => document.fonts.ready);
    pages.push(page);
  }
  const { FPS, DURATION } = await pages[0].evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const shot = async (page, t, opts) => { await page.evaluate(t => window.render(t), t); return page.screenshot(opts); };

  if (process.argv[2] === '--stills') {
    for (const t of process.argv[3].split(',').map(Number)) {
      await shot(pages[0], t, { path: path.join(outDir, `still_${String(t).replace('.', '_')}.png`) });
    }
    await browser.close();
    return;
  }

  const out = process.argv[2] || path.join(outDir, 'chiken_monitor_short.mp4');
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', path.join(outDir, 'mix.wav'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium',
    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
    '-t', String(DURATION), '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));

  const t0 = Date.now();
  for (let i = 0; i < total; i += WORKERS) {
    const bufs = await Promise.all(pages.map((p, k) =>
      i + k < total ? shot(p, (i + k) / FPS, { type: 'jpeg', quality: 96 }) : null));
    for (const b of bufs) if (b && !ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
