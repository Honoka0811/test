// render.html を 1 フレームずつ撮影して無音の mp4 にし、効果音用のイベント表を output/events.json に書き出す
// 使い方: node capture.js [出力mp4]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const out = process.argv[2] || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => { await Promise.all(['NotoBlack', 'NotoBold', 'Dela'].map(f => document.fonts.load(`100px "${f}"`, 'あA1'))); });
  const { FPS, DURATION, EVENTS } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION, EVENTS: window.EVENTS }));
  fs.writeFileSync(path.join(__dirname, 'output', 'events.json'), JSON.stringify(EVENTS, null, 1));
  const total = Math.ceil(FPS * DURATION);

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));

  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const dataUrl = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, i / FPS);
    const b = Buffer.from(dataUrl.split(',')[1], 'base64');
    if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
