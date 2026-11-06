// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(無音)にエンコードする
// 使い方: node capture.js [出力mp4]          … output/timings.json があればその実測タイミングを使う
//         node capture.js --stills 1,5,12   … 指定秒の静止画を output/still_*.png に書き出す(確認用。THUMB=1 で字幕なし)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const stills = args[0] === '--stills' ? args[1].split(',').map(Number) : null;
  const out = (!stills && args[0]) || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(path.join(__dirname, 'output'), { recursive: true });
  const tPath = path.join(__dirname, 'output', 'timings.json');
  const timings = fs.existsSync(tPath) ? JSON.parse(fs.readFileSync(tPath, 'utf8')) : null;
  console.log(timings ? 'timings: output/timings.json' : 'timings: 推定値(ナレーション未生成)');

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(([tm, th]) => { window.CAPTURE = true; window.THUMB = th; if (tm) window.TIMINGS = tm; }, [timings, !!process.env.THUMB]);
  page.on('pageerror', e => console.error('page error:', e));
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = (t) => page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)
    .then(u => Buffer.from(u.split(',')[1], 'base64'));

  if (stills) {
    for (const t of stills) { const f = path.join(__dirname, 'output', `still_${String(t).replace('.', '_')}.png`); fs.writeFileSync(f, await grab(t)); console.log('wrote', f); }
    await browser.close(); return;
  }
  const total = Math.round(FPS * DURATION);
  console.log(`duration ${DURATION.toFixed(2)}s, ${total} frames`);
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
