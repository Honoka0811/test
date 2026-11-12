// render.html を 1 フレームずつ撮影して ffmpeg で mp4 化し、output/mix.wav(ナレーション+BGM)を合成する
// 使い方: node capture.js [出力パス]   ※先に python3 narrate.py を実行しておく
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const out = process.argv[2] || path.join(__dirname, 'output', 'golf_ball_diver.mp4');
  const cues = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'cues.json'), 'utf8'));
  const mix = path.join(__dirname, 'output', 'mix.wav');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(c => { window.CUES = c; }, cues);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const total = Math.round(FPS * DURATION);

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-i', mix, '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium',
    '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-shortest', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));

  for (let i = 0; i < total; i++) {
    const dataUrl = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, i / FPS);
    if (!ff.stdin.write(Buffer.from(dataUrl.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
