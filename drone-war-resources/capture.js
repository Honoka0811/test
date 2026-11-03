// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする(タイミングは output/timing.json から)
// 使い方: node capture.js [出力パス]     サムネイルのみ: node capture.js --thumb
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const thumbOnly = process.argv.includes('--thumb');
  const out = process.argv.find((a, i) => i >= 2 && !a.startsWith('--')) || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const timing = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timing.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate((tm) => window.setTiming(tm), timing);

  // サムネイル
  const thumb = await page.evaluate(() => { window.renderThumbnail(); return document.getElementById('c').toDataURL('image/png'); });
  fs.writeFileSync(path.join(__dirname, 'output', 'thumbnail.png'), Buffer.from(thumb.split(',')[1], 'base64'));
  console.log('wrote thumbnail.png');
  if (thumbOnly) { await browser.close(); return; }

  const FPS = await page.evaluate(() => window.FPS);
  const total = Math.round(FPS * timing.total);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    const buf = Buffer.from(dataUrl.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 600 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
