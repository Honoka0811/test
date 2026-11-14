// render.html を 1 フレームずつ撮影し ffmpeg で mp4 化する
// 使い方: node capture.js [出力パス]   /   node capture.js --stills  (確認用の静止画のみ)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const stills = process.argv.includes('--stills');
  const out = process.argv.find((a, i) => i > 1 && !a.startsWith('--')) || path.join(__dirname, 'output', 'video_silent.mp4');
  const timings = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timings.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate((j) => window.setTimings(j), timings);
  const FPS = await page.evaluate(() => window.FPS);
  const frame = async (t) => Buffer.from((await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (stills) {
    const dir = path.join(__dirname, 'output', 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of timings.scenes) fs.writeFileSync(path.join(dir, `${s.id}.png`), await frame(s.start + s.dur - 0.3));
    fs.writeFileSync(path.join(__dirname, 'output', 'thumbnail.png'), await frame(timings.scenes[0].start + 2.5));
    await browser.close(); console.log('wrote stills'); return;
  }
  const total = Math.round(FPS * timings.total);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  for (let i = 0; i < total; i++) {
    const buf = await frame(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
