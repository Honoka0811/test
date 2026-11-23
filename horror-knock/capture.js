// render.html を 1 フレームずつ撮影して ffmpeg で mp4 にする
// 使い方:
//   node capture.js                      → output/video_silent.mp4(無音の映像)
//   node capture.js --stills 1.2,30.5    → output/stills/t_1.20.png など(確認用の静止画)
//   node capture.js --thumb              → output/thumbnail.png
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const OUT = path.join(__dirname, 'output');

(async () => {
  const args = process.argv.slice(2);
  const tl = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e); process.exit(1); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => {
    for (const w of [500, 700, 900]) await document.fonts.load(`${w} 64px NSerif`, 'あ午前時ノック');
    await document.fonts.ready;
  });
  await page.evaluate(tl => window.setTimeline(tl), tl);
  const grab = async (fn, t) => {
    const url = await page.evaluate(([fn, t]) => { window[fn](t); return document.getElementById('c').toDataURL('image/png'); }, [fn, t]);
    return Buffer.from(url.split(',')[1], 'base64');
  };

  if (args[0] === '--stills') {
    const dir = path.join(OUT, 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of args[1].split(',')) {
      const t = parseFloat(s);
      fs.writeFileSync(path.join(dir, `t_${t.toFixed(2)}.png`), await grab('render', t));
    }
    console.log('wrote stills to', dir);
  } else if (args[0] === '--thumb') {
    fs.writeFileSync(path.join(OUT, 'thumbnail.png'), await grab('renderThumb', 0));
    console.log('wrote', path.join(OUT, 'thumbnail.png'));
  } else {
    const out = args[0] || path.join(OUT, 'video_silent.mp4');
    const FPS = tl.fps, total = Math.ceil(tl.duration * FPS);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-tune', 'grain', '-movflags', '+faststart', out]);
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
    console.log('wrote', out);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
