// render.html を 1 フレームずつ撮影し、ffmpeg で無音の mp4 にする
// 使い方:
//   node capture.js                     → build/video.mp4
//   node capture.js --stills 1.2,8,40   → build/stills/t_1.20.png など(確認用の静止画)
//   node capture.js --thumb 39.2        → output/thumbnail.png
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.join(__dirname, 'render.html') + '?capture');
  await page.evaluate(() => window.READY);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = async (t) => {
    const url = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(url.split(',')[1], 'base64');
  };

  if (opt('--stills') || opt('--thumb')) {
    if (opt('--thumb')) await page.evaluate(() => { window.NO_SUB = true; });  // サムネは字幕なし
    const dir = opt('--thumb') ? path.join(__dirname, 'output') : path.join(__dirname, 'build', 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of (opt('--stills') || opt('--thumb')).split(',')) {
      const t = parseFloat(s);
      const f = opt('--thumb') ? path.join(dir, 'thumbnail.png') : path.join(dir, `t_${t.toFixed(2)}.png`);
      fs.writeFileSync(f, await grab(t)); console.log('wrote', f);
    }
    await browser.close(); return;
  }

  const out = path.join(__dirname, 'build', 'video.mp4');
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
