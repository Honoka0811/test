// render.html を 1 フレームずつ撮影して ffmpeg で mp4(無音)にする。
// 使い方: node capture.js [出力mp4]            … 全編
//         node capture.js --stills 1.2,5.0,...  … 指定秒の静止画を output/stills/ に保存(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(t => { window.TIMELINE = t; }, tl);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const grab = async t => Buffer.from((await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (process.argv[2] === '--stills') {
    const dir = path.join(__dirname, 'output', 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of process.argv[3].split(',')) { fs.writeFileSync(path.join(dir, `t${(+s).toFixed(2)}.png`), await grab(+s)); }
    await browser.close(); console.log('stills ->', dir); return;
  }
  const out = process.argv[2] || path.join(__dirname, 'output', 'video_silent.mp4');
  const FPS = 30, total = Math.round(tl.total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
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
