// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]
//         node capture.js --frames 1.5,6,12 [出力ディレクトリ]   指定秒のフレームを PNG で書き出す(確認・サムネイル用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const framesOnly = args[0] === '--frames';
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  // ナレーションエンジンのクレジット表記(narrate.py が output/credit.txt に書く)
  const creditFile = path.join(__dirname, 'output', 'credit.txt');
  if (fs.existsSync(creditFile)) {
    const credit = fs.readFileSync(creditFile, 'utf8').trim();
    await page.evaluate((c) => { window.CREDIT = c; }, credit);
    console.log('credit:', credit);
  }
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const shot = async (t) => {
    const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(dataUrl.split(',')[1], 'base64');
  };

  if (framesOnly) {
    const dir = args[2] || path.join(__dirname, 'output', 'frames');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of args[1].split(',')) {
      const t = parseFloat(s);
      const f = path.join(dir, `t${t.toFixed(2).replace('.', '_')}.png`);
      fs.writeFileSync(f, await shot(t));
      console.log('wrote', f);
    }
    await browser.close();
    return;
  }

  const out = args[0] || path.join(__dirname, 'output', 'nihon_sandai.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
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
