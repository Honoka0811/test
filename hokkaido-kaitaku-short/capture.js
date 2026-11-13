// render.html を 1 フレームずつ撮影し、ffmpeg で無音の mp4 にする(4 並列で区間ごとに撮って連結)
// 使い方: node capture.js
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path'); const fs = require('fs');
const OUT = path.join(__dirname, 'out'); const WORKERS = 4;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(async () => { window.render(0); for (const f of ['800 10px Mincho', '900 10px Sans', '700 10px Sans', '500 10px Sans']) await document.fonts.load(f); await document.fonts.ready; });
  return page;
}
async function segment(browser, k, from, to, FPS) {
  const page = await openPage(browser); const file = path.join(OUT, `seg${k}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-g', String(FPS * 2), file]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  for (let i = from; i < to; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1080, height: 1920 } });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (k === 0 && (i - from) % 60 === 0) console.log(`worker0 frame ${i - from}/${to - from}`);
  }
  ff.stdin.end(); await done; await page.close(); return file;
}
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const p0 = await openPage(browser);
  const { FPS, DURATION } = await p0.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  await p0.evaluate(() => window.render(2.95)); await p0.screenshot({ path: path.join(OUT, 'thumbnail.jpg'), quality: 92 }); await p0.close();
  const total = Math.round(FPS * DURATION), per = Math.ceil(total / WORKERS);
  const files = await Promise.all([...Array(WORKERS).keys()].map(k => segment(browser, k, k * per, Math.min(total, (k + 1) * per), FPS)));
  await browser.close();
  const list = path.join(OUT, 'segs.txt'); fs.writeFileSync(list, files.map(f => `file '${f}'`).join('\n'));
  const out = path.join(OUT, 'video_silent.mp4');
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', out]);
  files.forEach(f => fs.unlinkSync(f)); fs.unlinkSync(list);
  console.log('wrote', out, total, 'frames');
})().catch(e => { console.error(e); process.exit(1); });
