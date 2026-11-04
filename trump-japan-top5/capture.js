// render.html を 1 フレームずつ撮影して ffmpeg で mp4 化する
// 使い方:
//   node capture.js                 → output/video_silent.mp4
//   node capture.js stills 1,5.5,20 → output/still_<t>.png(確認用)
//   node capture.js thumb           → output/thumbnail.png
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const mode = process.argv[2] || 'video';
  const out = path.join(__dirname, 'output');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => {
    await Promise.all(['900', '700', '500'].map(w => document.fonts.load(`${w} 60px NJP`, 'あ漢A')));
    await document.fonts.ready;
  });
  const grab = async (fn, arg) => Buffer.from((await page.evaluate(([fn, arg]) => {
    window[fn](arg); return document.getElementById('c').toDataURL('image/png');
  }, [fn, arg])).split(',')[1], 'base64');

  if (mode === 'stills') {
    for (const t of process.argv[3].split(',').map(Number)) {
      fs.writeFileSync(path.join(out, `still_${t}.png`), await grab('render', t));
    }
  } else if (mode === 'thumb') {
    fs.writeFileSync(path.join(out, 'thumbnail.png'), await grab('renderThumb'));
  } else {
    const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
    const total = Math.ceil(FPS * DURATION);
    const dst = path.join(out, 'video_silent.mp4');
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', dst]);
    ff.stderr.on('data', d => process.stderr.write(d));
    const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
    const t0 = Date.now();
    for (let i = 0; i < total; i++) {
      const buf = await grab('render', i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    }
    ff.stdin.end();
    await done;
    console.log('wrote', dst);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
