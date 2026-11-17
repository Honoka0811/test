// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(無音)にエンコードする
// 使い方: node capture.js [出力パス]      /  node capture.js --shots 1.5,8,15 (確認用の静止画を output/shots/ に書き出す)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.goto('file://' + path.join(__dirname, 'render.html') + '?capture');
  await page.waitForFunction(() => window.READY === true);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = async (t, type, q) => Buffer.from((await page.evaluate(([t, type, q]) => {
    window.render(t); return document.getElementById('c').toDataURL(type, q);
  }, [t, type, q])).split(',')[1], 'base64');

  if (process.argv[2] === '--shots') {
    const dir = path.join(__dirname, 'output', 'shots'); fs.mkdirSync(dir, { recursive: true });
    for (const s of process.argv[3].split(',')) fs.writeFileSync(path.join(dir, `t${s}.jpg`), await grab(parseFloat(s), 'image/jpeg', 0.8));
    await browser.close(); return;
  }

  const out = process.argv[2] || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
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
