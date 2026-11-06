// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(映像のみ)にエンコードする
// 使い方: node capture.js [出力パス]            … 動画
//         node capture.js --stills 1.0 5.2 ...  … 指定秒の静止画を output/stills/ に保存
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.error('[pageerror]', e));
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => { await document.fonts.load('80px Dela'); await document.fonts.load('80px MRound'); await document.fonts.ready; });
  const fontsOk = await page.evaluate(() => document.fonts.check('80px Dela') && document.fonts.check('80px MRound'));
  console.log('fonts loaded:', fontsOk);
  const grab = async t => Buffer.from((await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (args[0] === '--stills') {
    const dir = path.join(__dirname, 'output', 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of args.slice(1)) { fs.writeFileSync(path.join(dir, `t${s}.png`), await grab(parseFloat(s))); }
    await browser.close(); return;
  }
  const out = args[0] || path.join(__dirname, 'output', 'video_only.mp4');
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const total = Math.round(FPS * DURATION);
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
