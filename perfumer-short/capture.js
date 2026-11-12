// render.html を 1 フレームずつ撮影して ffmpeg で mp4(無音)にする
// 使い方: node capture.js [出力mp4]         静止画だけ: node capture.js --stills 1,10,20
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const stills = args[0] === '--stills' ? args[1].split(',').map(Number) : null;
  const out = (!stills && args[0]) || path.join(__dirname, 'output', 'video_silent.mp4');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => {
    await Promise.all(['500', '700', '900'].map(w => document.fonts.load(`${w} 50px ZenMaru`)));
    await document.fonts.load('50px "Noto Color Emoji"', '🌸');
    document.querySelector('canvas').style.cssText = 'width:1080px;height:1920px';
  });
  const grab = async t => Buffer.from((await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (stills) {
    fs.mkdirSync(path.join(__dirname, 'output', 'stills'), { recursive: true });
    for (const t of stills) fs.writeFileSync(path.join(__dirname, 'output', 'stills', `t${t}.png`), await grab(t));
    await browser.close(); return;
  }
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const total = Math.ceil(FPS * DURATION);
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
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
