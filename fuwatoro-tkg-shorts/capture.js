// render.html を 1 フレームずつ撮影し、ffmpeg で無音の mp4 にエンコードする
// 使い方: node capture.js                      → output/video.mp4
//         node capture.js --stills 1,3.5,10    → 指定秒の静止画を output/stills/ に書き出す(確認用)
//         node capture.js --thumb              → output/thumbnail.png
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const outDir = path.join(__dirname, 'output'); fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => {
    await Promise.all(['"Dela Gothic One"', '"Noto Sans JP Black"', '"M PLUS 1p Black"', '"Noto Color Emoji"'].map(f => document.fonts.load(`80px ${f}`, 'ふわとろ卵🥚')));
    await document.fonts.ready;
  });
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const frame = async (t) => Buffer.from((await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (args[0] === '--stills') {
    const dir = path.join(outDir, 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of args[1].split(',')) { fs.writeFileSync(path.join(dir, `t${Number(s).toFixed(2)}.png`), await frame(Number(s))); }
    console.log('wrote stills'); await browser.close(); return;
  }
  if (args[0] === '--thumb') {
    const b = Buffer.from((await page.evaluate(() => { window.renderThumbnail(); return document.getElementById('c').toDataURL('image/png'); })).split(',')[1], 'base64');
    fs.writeFileSync(path.join(outDir, 'thumbnail.png'), b); console.log('wrote output/thumbnail.png'); await browser.close(); return;
  }
  const out = args[0] || path.join(outDir, 'video.mp4');
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await frame(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out, `(${total} frames, ${DURATION}s)`);
})().catch(e => { console.error(e); process.exit(1); });
