// render.html を 1 フレームずつ撮影して mp4 にする。
// 使い方: node capture.js                … output/video_silent.mp4 を書き出す
//         node capture.js --still 4.9 a.png … 指定秒の静止画だけ書き出す(確認・サムネイル用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const timings = fs.readFileSync(path.join(__dirname, 'output', 'timings.json'), 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.addInitScript(`window.TIMINGS = ${timings};`);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = (t, type, q) => page.evaluate(([t, type, q]) => {
    window.render(t); return document.getElementById('c').toDataURL(type, q);
  }, [t, type, q]).then(u => Buffer.from(u.split(',')[1], 'base64'));

  const args = process.argv.slice(2);
  if (args[0] === '--still') {
    for (let i = 1; i + 1 < args.length; i += 2) {
      fs.writeFileSync(args[i + 1], await grab(parseFloat(args[i]), 'image/png'));
      console.log('wrote', args[i + 1]);
    }
    await browser.close(); return;
  }

  const out = args[0] || path.join(__dirname, 'output', 'video_silent.mp4');
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '14', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS, 'image/jpeg', 0.97);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
