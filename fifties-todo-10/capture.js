// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力パス]
//        node capture.js --frames 1.0,5.2,12.0 [出力ディレクトリ]   指定秒のフレームを PNG で書き出す(確認用)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'warning' || m.type() === 'error') console.log('[page]', m.text()); });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.ready);
  const tl = path.join(__dirname, 'output', 'timeline.json');
  if (fs.existsSync(tl)) {
    const { durations: durs, subtitles } = JSON.parse(fs.readFileSync(tl, 'utf8'));
    await page.evaluate(([d, s]) => window.setTimeline(d, s), [durs, subtitles]);
    console.log('timeline:', durs.map(d => d.toFixed(2)).join(' '));
  }
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));

  if (args[0] === '--frames') {
    const times = args[1].split(',').map(Number);
    const dir = args[2] || path.join(__dirname, 'output', 'frames');
    fs.mkdirSync(dir, { recursive: true });
    for (const t of times) {
      const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
      const f = path.join(dir, `t${t.toFixed(2).replace('.', '_')}.png`);
      fs.writeFileSync(f, Buffer.from(dataUrl.split(',')[1], 'base64'));
      console.log('wrote', f);
    }
    await browser.close();
    return;
  }

  const out = args[0] || path.join(__dirname, 'output', 'fifties_todo_10.mp4');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));

  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    const buf = Buffer.from(dataUrl.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out, `(${total} frames, ${DURATION}s)`);
})().catch(e => { console.error(e); process.exit(1); });
