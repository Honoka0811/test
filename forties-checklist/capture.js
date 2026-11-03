// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(無音)にエンコードする
// 使い方: node capture.js [出力mp4] [timing.json]
//   環境変数 PREVIEW_TIMES="0.5,4,10" を指定すると、その時刻の PNG だけを output/preview/ に書き出す
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const out = process.argv[2] || path.join(__dirname, 'output', 'forties_checklist.mp4');
  const timingPath = process.argv[3] || path.join(__dirname, 'output', 'timing.json');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.ready);
  await page.evaluate(() => document.fonts.ready);
  if (fs.existsSync(timingPath)) {
    const timing = JSON.parse(fs.readFileSync(timingPath, 'utf8'));
    await page.evaluate(t => window.setTiming(t), timing);
  } else {
    console.warn('timing.json が無いのでプレビュー用の既定尺で描画します');
  }
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const frameAt = async (t) => {
    const dataUrl = await page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(dataUrl.split(',')[1], 'base64');
  };

  if (process.env.PREVIEW_TIMES) {
    const dir = path.join(__dirname, 'output', 'preview'); fs.mkdirSync(dir, { recursive: true });
    for (const s of process.env.PREVIEW_TIMES.split(',')) {
      const t = parseFloat(s); fs.writeFileSync(path.join(dir, `t${t.toFixed(2)}.png`), await frameAt(t));
    }
    await browser.close(); console.log('wrote previews to', dir); return;
  }

  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await frameAt(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', out, `(${DURATION}s, ${total} frames)`);
})().catch(e => { console.error(e); process.exit(1); });
