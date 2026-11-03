// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]            … 動画を書き出す
//         node capture.js --frames 2.5,7,30   … 指定秒のフレームを output/frame_*.png に書き出す(確認用)
//         node capture.js --thumb 2.6         … サムネイル output/thumbnail.png を書き出す
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const outDir = path.join(__dirname, 'output');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const shot = async (t) => {
    const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(dataUrl.split(',')[1], 'base64');
  };

  if (args[0] === '--frames') {
    for (const s of args[1].split(',')) {
      const t = parseFloat(s);
      fs.writeFileSync(path.join(outDir, `frame_${t.toFixed(2)}.png`), await shot(t));
    }
    await browser.close(); return;
  }
  if (args[0] === '--thumb') {
    fs.writeFileSync(path.join(outDir, 'thumbnail.png'), await shot(parseFloat(args[1] || '2.6')));
    await browser.close(); return;
  }

  const out = args[0] || path.join(outDir, 'twenties_10.mp4');
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await shot(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
