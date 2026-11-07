// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]                 … 動画を書き出す(output/video_silent.mp4)
//         node capture.js --thumb [out.png]          … サムネイル専用フレームを書き出す
//         node capture.js --stills 1.2,7.5,13 [dir] … 指定秒の静止画 PNG を書き出す(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const stills = args[0] === '--stills' ? args[1].split(',').map(Number) : null;
  const out = args[0] === '--thumb' ? path.join(__dirname, 'output') : stills ? (args[2] || path.join(__dirname, 'output', 'stills')) : (args[0] || path.join(__dirname, 'output', 'video_silent.mp4'));
  fs.mkdirSync(stills ? out : path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('pageerror', e));
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  // file:// では fetch が使えないので字幕データを注入
  const capPath = path.join(__dirname, 'output', 'captions.json');
  if (fs.existsSync(capPath)) await page.evaluate(c => window.setCaptions(c), JSON.parse(fs.readFileSync(capPath, 'utf8')));
  else console.warn('captions.json が無いので字幕なしで描画します(先に narrate.py を実行してください)');
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = async t => Buffer.from((await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (args[0] === '--thumb') {
    const dst = args[1] || path.join(__dirname, 'output', 'thumbnail.png');
    const url = await page.evaluate(() => { window.renderThumb(); return document.getElementById('c').toDataURL('image/png'); });
    fs.writeFileSync(dst, Buffer.from(url.split(',')[1], 'base64'));
    await browser.close(); console.log('wrote', dst); return;
  }
  if (stills) {
    for (const t of stills) { fs.writeFileSync(path.join(out, `t${t.toFixed(2)}.png`), await grab(t)); }
    await browser.close(); console.log('wrote', stills.length, 'stills to', out); return;
  }
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
