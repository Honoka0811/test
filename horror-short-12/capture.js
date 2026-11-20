// render.html を 1 フレームずつ描画して ffmpeg に流し込み、無音の mp4 を作る
// 使い方: node capture.js            → output/silent.mp4
//         node capture.js shots 1.5 9.3 ...  → output/frames/ に指定秒の静止画だけ書き出す(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
const here = __dirname, out = path.join(here, 'output');

(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(here, 'timeline.json')));
  tl.ev = JSON.parse(fs.readFileSync(path.join(here, 'events.json')));
  fs.writeFileSync(path.join(here, 'data.js'), 'window.DATA = ' + JSON.stringify(tl) + ';\n');
  fs.mkdirSync(path.join(out, 'frames'), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('PAGE ERROR', e); process.exit(1); });
  await page.goto('file://' + path.join(here, 'render.html'));
  await page.evaluate(() => window.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = async (t, type, q) => Buffer.from((await page.evaluate(([t, type, q]) => { window.render(t); return document.getElementById('c').toDataURL(type, q); }, [t, type, q])).split(',')[1], 'base64');

  if (process.argv[2] === 'shots') {
    for (const s of process.argv.slice(3)) fs.writeFileSync(path.join(out, 'frames', `t${s}.jpg`), await grab(parseFloat(s), 'image/jpeg', 0.85));
    await browser.close(); return;
  }
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', path.join(out, 'silent.mp4')]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS, 'image/jpeg', 0.97);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote output/silent.mp4');
})().catch(e => { console.error(e); process.exit(1); });
