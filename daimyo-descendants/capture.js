// render.html を 1 フレームずつ撮影して mp4(映像のみ)にする。並列ワーカーで区間ごとに書き出して結合。
// 使い方:
//   node capture.js                    -> output/video_silent.mp4
//   node capture.js --stills 3,40,120  -> output/still_<t>.png(確認用)
//   node capture.js --thumb            -> output/thumbnail.png(1280x720)
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const HERE = __dirname, OUT = path.join(HERE, 'output');
const script = JSON.parse(fs.readFileSync(path.join(HERE, 'script.json'), 'utf8'));
const tl = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));
const FPS = 30;
const args = process.argv.slice(2);

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(HERE, 'render.html'));
  await page.evaluate(async ([s, t]) => {
    window.setData(s, t);
    await document.fonts.load('800 50px Mincho'); await document.fonts.load('700 50px Goth');
    await document.fonts.ready;
  }, [script, tl]);
  return page;
}
const grab = (page, fn, t, type = 'image/jpeg') => page.evaluate(([fn, t, type]) => {
  window[fn](t); return document.getElementById('c').toDataURL(type, 0.93);
}, [fn, t, type]).then(u => Buffer.from(u.split(',')[1], 'base64'));

async function worker(browser, from, to, file, id) {
  const page = await openPage(browser);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-r', String(FPS), file]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  for (let i = from; i < to; i++) {
    const buf = await grab(page, 'render', i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((i - from) % 600 === 0) console.log(`[w${id}] frame ${i - from}/${to - from}`);
  }
  ff.stdin.end(); await done; await page.close();
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  if (args[0] === '--stills') {
    const page = await openPage(browser);
    for (const t of args[1].split(',').map(Number)) {
      const f = path.join(OUT, `still_${t}.png`);
      fs.writeFileSync(f, await grab(page, 'render', t, 'image/png')); console.log('wrote', f);
    }
  } else if (args[0] === '--thumb') {
    const page = await openPage(browser);
    const f = path.join(OUT, 'thumbnail_full.png');
    fs.writeFileSync(f, await grab(page, 'renderThumb', 0, 'image/png'));
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', f, '-vf', 'scale=1280:720:flags=lanczos', path.join(OUT, 'thumbnail.png')]);
    fs.unlinkSync(f); console.log('wrote output/thumbnail.png');
  } else {
    const total = Math.ceil(tl.total * FPS), N = 4, per = Math.ceil(total / N);
    const parts = [...Array(N).keys()].map(k => path.join(OUT, `part${k}.mp4`));
    const t0 = Date.now();
    await Promise.all(parts.map((f, k) => worker(browser, k * per, Math.min(total, (k + 1) * per), f, k)));
    const list = path.join(OUT, 'parts.txt');
    fs.writeFileSync(list, parts.map(p => `file '${p}'`).join('\n'));
    const out = path.join(OUT, 'video_silent.mp4');
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out]);
    parts.forEach(p => fs.unlinkSync(p)); fs.unlinkSync(list);
    console.log(`wrote ${out} (${total} frames, ${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
