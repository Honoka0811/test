// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする(音声なし)
// 使い方: node capture.js [出力パス]           … 動画を書き出す
//         node capture.js --stills 1,10,30 dir  … 指定秒の静止画を書き出す(確認用)
// output/cues.json(narrate.py が生成)があれば字幕を焼き込む
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const stills = args[0] === '--stills' ? args[1].split(',').map(Number) : null;
  const out = stills ? (args[2] || path.join(__dirname, 'output', 'stills')) : (args[0] || path.join(__dirname, 'output', 'video_silent.mp4'));
  fs.mkdirSync(stills ? out : path.dirname(out), { recursive: true });
  const cuesPath = path.join(__dirname, 'output', 'cues.json');
  const cues = fs.existsSync(cuesPath) ? JSON.parse(fs.readFileSync(cuesPath, 'utf8')) : [];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate((c) => { window.CUES = c; return document.fonts.ready; }, cues);
  const grab = (t) => page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)
    .then(u => Buffer.from(u.split(',')[1], 'base64'));

  if (stills) {
    for (const t of stills) fs.writeFileSync(path.join(out, `t${String(t).padStart(5, '0')}.png`), await grab(t));
    await browser.close(); console.log('wrote stills to', out); return;
  }
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
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
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
