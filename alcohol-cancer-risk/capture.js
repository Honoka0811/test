// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]
//         node capture.js --stills 3,10,20 [出力ディレクトリ]   (確認用の静止画 PNG を書き出す)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const frame = async (t) => {
    const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(dataUrl.split(',')[1], 'base64');
  };

  if (process.argv[2] === '--stills') {
    const times = process.argv[3].split(',').map(Number);
    const dir = process.argv[4] || path.join(__dirname, 'output', 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const t of times) {
      const f = path.join(dir, `t${t.toFixed(1).replace('.', '_')}.png`);
      fs.writeFileSync(f, await frame(t));
      console.log('wrote', f);
    }
    await browser.close();
    return;
  }

  const out = process.argv[2] || path.join(__dirname, 'output', 'alcohol_cancer_risk.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await frame(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
