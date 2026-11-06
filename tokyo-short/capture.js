// render.html を 1 フレームずつ撮影し ffmpeg で mp4(無音)にする
// 使い方: node capture.js            → output/video.mp4
//        node capture.js --stills 1.0 6.5 ...  → output/stills/*.png(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => { window.__CAPTURE__ = true; });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async (tl) => { window.setTimeline(tl); await document.fonts.load('80px Dela'); await document.fonts.load('80px Maru'); await document.fonts.ready; }, tl);
  const grab = async (t) => Buffer.from((await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  const si = process.argv.indexOf('--stills');
  if (si > 0) {
    const dir = path.join(__dirname, 'output', 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const a of process.argv.slice(si + 1)) fs.writeFileSync(path.join(dir, `t${(+a).toFixed(2)}.png`), await grab(+a));
    await browser.close(); return;
  }
  const FPS = 30, total = Math.round(tl.total * FPS);
  const out = path.join(__dirname, 'output', 'video.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
