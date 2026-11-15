// render.html を 1 フレームずつ撮影して mp4(無音)にする。
// 使い方: node capture.js [出力mp4] [--frames 0,90,300 → PNG をoutput/frame_N.png に書き出して終了]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const ROOT = __dirname;
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  const type = { '.html': 'text/html; charset=utf-8', '.ttf': 'font/ttf', '.json': 'application/json' }[path.extname(p)] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': type }); fs.createReadStream(p).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const args = process.argv.slice(2);
  const fi = args.indexOf('--frames');
  const frames = fi >= 0 ? args[fi + 1].split(',').map(Number) : null;
  const out = (fi === 0 ? null : args[0]) || path.join(ROOT, 'output', 'video_silent.mp4');
  const timings = JSON.parse(fs.readFileSync(path.join(ROOT, 'output', 'timings.json'), 'utf8'));

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${port}/render.html`);
  await page.evaluate(async (tm) => {
    window.TIMINGS = tm;
    await Promise.all(['72px Dela', '72px Maru', '72px "Noto Color Emoji"'].map(f => document.fonts.load(f, 'あ1🌍')));
    await document.fonts.ready;
  }, timings);
  const FPS = await page.evaluate(() => window.FPS);
  const grab = async (t) => Buffer.from((await page.evaluate((t) => {
    window.render(t); return document.getElementById('c').toDataURL('image/png');
  }, t)).split(',')[1], 'base64');

  if (frames) {
    for (const t of frames) fs.writeFileSync(path.join(ROOT, 'output', `frame_${t}.png`), await grab(t));
    console.log('wrote frames', frames.join(','));
  } else {
    const total = Math.ceil(timings.duration * FPS);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
    const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
    const t0 = Date.now();
    for (let i = 0; i < total; i++) {
      const buf = await grab(i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    }
    ff.stdin.end(); await done;
    console.log('wrote', out);
  }
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
