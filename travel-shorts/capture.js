// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする。
// 使い方: node capture.js [出力mp4]            … 全フレーム撮影
//         node capture.js --frame 12.5 out.png … 1 フレームだけ PNG で書き出す(プレビュー用)
//         node capture.js --thumb out.png       … サムネイルを書き出す
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const timeline = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => { window.__capture = true; });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(tl => window.setTimeline(tl), timeline);
  const FPS = await page.evaluate(() => window.FPS);

  if (args[0] === '--frame') {
    const t = parseFloat(args[1]); const out = args[2] || `frame_${t}.png`;
    const dataUrl = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    fs.writeFileSync(out, Buffer.from(dataUrl.split(',')[1], 'base64'));
    await browser.close(); console.log('wrote', out); return;
  }
  if (args[0] === '--thumb') {
    const out = args[1] || 'thumbnail.png';
    const dataUrl = await page.evaluate(() => { window.renderThumb(); return document.getElementById('c').toDataURL('image/png'); });
    fs.writeFileSync(out, Buffer.from(dataUrl.split(',')[1], 'base64'));
    await browser.close(); console.log('wrote', out); return;
  }
  if (args[0] === '--frames') {  // 複数時刻をまとめて: --frames "1,5.2,10" outdir
    const ts = args[1].split(',').map(Number); const dir = args[2]; fs.mkdirSync(dir, { recursive: true });
    for (const t of ts) { const dataUrl = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t); fs.writeFileSync(path.join(dir, `f_${t.toFixed(2)}.png`), Buffer.from(dataUrl.split(',')[1], 'base64')); }
    await browser.close(); console.log('wrote', ts.length, 'frames to', dir); return;
  }
  const out = args[0] || path.join(__dirname, 'output', 'video_silent.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const total = Math.round(FPS * timeline.total);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-maxrate', '14M', '-bufsize', '28M', '-preset', 'slow', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    const dataUrl = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, t);
    const buf = Buffer.from(dataUrl.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out, `(${((Date.now() - t0) / 1000).toFixed(1)}s)`);
})().catch(e => { console.error(e); process.exit(1); });
