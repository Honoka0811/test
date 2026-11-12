// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(無音)にエンコードする
// 使い方: node capture.js [出力mp4]
//         node capture.js --stills 3,13.5,20   … 指定秒の静止画を output/stills/ に書き出す(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const stillsAt = process.argv[2] === '--stills' ? process.argv[3].split(',').map(Number) : null;
  const out = (!stillsAt && process.argv[2]) || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(path.join(__dirname, 'output', 'stills'), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const shot = async (t, type, q) => Buffer.from((await page.evaluate(([t, type, q]) => {
    window.render(t); return document.getElementById('c').toDataURL(type, q);
  }, [t, type, q])).split(',')[1], 'base64');

  if (stillsAt) {
    for (const t of stillsAt) {
      const f = path.join(__dirname, 'output', 'stills', `t${t.toFixed(1).padStart(5, '0')}.png`);
      fs.writeFileSync(f, await shot(t, 'image/png'));
      console.log('wrote', f);
    }
    await browser.close();
    return;
  }

  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await shot(i / FPS, 'image/jpeg', 0.96);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
