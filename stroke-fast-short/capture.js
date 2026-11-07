// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]   /  node capture.js --thumb [出力png]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const thumb = process.argv[2] === '--thumb';
  const out = (thumb ? process.argv[3] : process.argv[2]) || path.join(__dirname, 'output', thumb ? 'thumbnail.png' : 'stroke_fast.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const timeline = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timeline.json'), 'utf8'));
  const events = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'events.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(({ tl, ev }) => window.setData(tl, ev), { tl: timeline, ev: events });
  // フォントを確実に読み込む
  await page.evaluate(() => document.fonts.load('bold 48px "Noto Sans CJK JP"'));
  await page.evaluate(() => document.fonts.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));

  const grab = async (expr) => {
    const dataUrl = await page.evaluate((e) => { eval(e); return document.getElementById('c').toDataURL('image/png'); }, expr);
    return Buffer.from(dataUrl.split(',')[1], 'base64');
  };
  if (thumb) {
    fs.writeFileSync(out, await grab('window.renderThumb()'));
    await browser.close(); console.log('wrote', out); return;
  }
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(`window.render(${i / FPS})`);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out, `${total} frames`);
})().catch(e => { console.error(e); process.exit(1); });
