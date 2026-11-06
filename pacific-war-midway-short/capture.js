// render.html を 1 フレームずつ撮影して ffmpeg で mp4(無音)にする。効果音用のイベント表も書き出す。
// 使い方: node capture.js            → output/video_silent.mp4, output/events.json
//         node capture.js --stills 1.0 5.2 ...  → output/stills/*.png(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
const OUT = path.join(__dirname, 'output');

(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => { console.error('[page error]', e); process.exit(1); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  const info = await page.evaluate(async (tl) => {
    const r = window.init(tl);
    // 使う文字をすべて含めてフォントを先読み(unicode-range 分割フォント対策)
    const chars = [...new Set(document.documentElement.innerHTML + JSON.stringify(tl))].join('');
    for (const f of ['900 80px "Noto Sans JP"', '700 80px "Noto Sans JP"', '400 80px "Dela Gothic One"']) await document.fonts.load(f, chars);
    await document.fonts.ready;
    return r;
  }, tl);
  fs.writeFileSync(path.join(OUT, 'events.json'), JSON.stringify(info.events, null, 1));
  const grab = async t => Buffer.from((await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  const si = process.argv.indexOf('--stills');
  if (si > 0) {
    fs.mkdirSync(path.join(OUT, 'stills'), { recursive: true });
    for (const a of process.argv.slice(si + 1)) { const f = path.join(OUT, 'stills', `t${(+a).toFixed(2)}.png`); fs.writeFileSync(f, await grab(+a)); console.log(f); }
    await browser.close(); return;
  }
  const FPS = 30, total = Math.ceil(info.duration * FPS), out = path.join(OUT, 'video_silent.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
