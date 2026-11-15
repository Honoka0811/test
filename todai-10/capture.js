// render.html を 1 フレームずつ撮影して mp4(無音)にする
// 使い方: node capture.js [出力mp4]       プレビュー: node capture.js --still 12.3 out.png
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const timeline = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async (tl) => {
    await Promise.all([document.fonts.load('500 40px MR', '東京'), document.fonts.load('800 40px MR', '東京')]);
    await document.fonts.ready; window.setTimeline(tl);
  }, timeline);
  const grab = t => page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)
    .then(u => Buffer.from(u.split(',')[1], 'base64'));

  if (args[0] === '--still') {
    for (let k = 1; k + 1 < args.length; k += 2) fs.writeFileSync(args[k + 1], await grab(+args[k]));
    await browser.close(); return;
  }
  const out = args[0] || path.join(__dirname, 'output', 'video_silent.mp4');
  const FPS = 30, total = Math.round(timeline.total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
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
