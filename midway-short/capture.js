// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4] [--frames]  (--frames: 各文の中間フレームを output/frames/*.png に書き出すだけ)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const framesOnly = args.includes('--frames');
  const out = args.find(a => !a.startsWith('--')) || path.join(__dirname, 'output', 'midway_short_silent.mp4');
  const timing = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timing.json'), 'utf8'));
  // photos/<scene id>.jpg|png があれば写真として使う
  const photos = {};
  for (const sc of timing.scenes) for (const ext of ['jpg', 'jpeg', 'png']) {
    const p = path.join(__dirname, 'photos', `${sc.id}.${ext}`);
    if (fs.existsSync(p)) { photos[sc.id] = 'file://' + p; break; }
  }
  console.log('photos:', Object.keys(photos).length ? Object.keys(photos).join(', ') : '(none; 図解で描画)');

  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => { window.__capture = true; });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(async ({ timing, photos }) => {
    window.setTiming(timing);
    window.PHOTOS = {};
    await Promise.all(Object.entries(photos).map(([id, src]) => new Promise((res) => {
      const im = new Image(); im.onload = () => { window.PHOTOS[id] = im; res(); }; im.onerror = () => res(); im.src = src;
    })));
  }, { timing, photos });
  const FPS = timing.fps, DURATION = timing.duration;

  // サムネイル
  fs.mkdirSync(path.join(__dirname, 'output'), { recursive: true });
  const th = await page.evaluate(() => { window.thumbnail(); return document.getElementById('c').toDataURL('image/png'); });
  fs.writeFileSync(path.join(__dirname, 'output', 'thumbnail.png'), Buffer.from(th.split(',')[1], 'base64'));

  if (framesOnly) {
    const dir = path.join(__dirname, 'output', 'frames'); fs.mkdirSync(dir, { recursive: true });
    for (const sc of timing.scenes) for (let i = 0; i < sc.subs.length; i++) {
      const s = sc.subs[i]; const t = (s.start + s.end) / 2;
      const d = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
      fs.writeFileSync(path.join(dir, `${sc.id}_${i}.png`), Buffer.from(d.split(',')[1], 'base64'));
    }
    await browser.close(); console.log('wrote', dir); return;
  }

  const total = Math.ceil(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'medium', '-movflags', '+faststart', out]);
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
