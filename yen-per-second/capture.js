// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]
//         node capture.js --thumb [出力png]          サムネイルだけ書き出す
//         node capture.js --preview [秒,秒,...] [出力dir]  指定時刻の静止画を書き出す(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const png = async (fn, arg) => Buffer.from((await page.evaluate(fn, arg)).split(',')[1], 'base64');

  if (args[0] === '--thumb') {
    const out = args[1] || path.join(__dirname, 'output', 'thumbnail.png');
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, await png(() => { window.thumbnail(); return document.getElementById('c').toDataURL('image/png'); }));
    console.log('wrote', out); await browser.close(); return;
  }
  if (args[0] === '--preview') {
    const times = (args[1] || '0').split(',').map(Number);
    const dir = args[2] || path.join(__dirname, 'output', 'preview');
    fs.mkdirSync(dir, { recursive: true });
    for (const t of times) {
      const f = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
      fs.writeFileSync(f, await png((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t));
      console.log('wrote', f);
    }
    await browser.close(); return;
  }

  const out = args[0] || path.join(__dirname, 'output', 'yen_per_second.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const total = Math.round(FPS * DURATION);

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));

  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    const buf = await png((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
