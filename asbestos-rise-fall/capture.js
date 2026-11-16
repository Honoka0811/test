// render.html を 1 フレームずつ描画し、ffmpeg で mp4 にエンコードする
// 使い方: node capture.js [出力mp4]            … 全編を書き出す(4 並列)
//         node capture.js --shots 1.5,8,20 …   … 指定秒の静止画を output/shots/ に書き出す(確認用)
const { chromium } = require('playwright');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const URL = 'file://' + path.join(__dirname, 'render.html');
const OUT = path.join(__dirname, 'output');

async function open(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exitCode = 1; });
  await page.goto(URL);
  await page.evaluate(() => window.ready);
  return page;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  if (process.argv[2] === '--shots') {
    const page = await open(browser);
    const dir = path.join(OUT, 'shots'); fs.mkdirSync(dir, { recursive: true });
    for (const s of process.argv[3].split(',')) {
      const t = parseFloat(s);
      const url = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.8); }, t);
      fs.writeFileSync(path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
    }
    await browser.close(); return;
  }
  const out = process.argv[2] || path.join(OUT, 'video_silent.mp4');
  const probe = await open(browser);
  const { FPS, DURATION } = await probe.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  await probe.close();
  const total = Math.round(FPS * DURATION), N = 4, per = Math.ceil(total / N);
  const t0 = Date.now();
  const parts = await Promise.all([...Array(N).keys()].map(async k => {
    const page = await open(browser);
    const part = path.join(OUT, `part${k}.mp4`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', part]);
    ff.stderr.on('data', d => process.stderr.write(d));
    const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
    for (let i = k * per; i < Math.min(total, (k + 1) * per); i++) {
      const url = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.97); }, i / FPS);
      if (!ff.stdin.write(Buffer.from(url.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if (k === 0 && i % 150 === 0) console.log(`frame ${i * N}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await done; return part;
  }));
  await browser.close();
  const list = path.join(OUT, 'parts.txt');
  fs.writeFileSync(list, parts.map(p => `file '${p}'`).join('\n'));
  const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', out], { stdio: 'inherit' });
  parts.forEach(p => fs.unlinkSync(p)); fs.unlinkSync(list);
  if (r.status !== 0) process.exit(1);
  console.log('wrote', out, `${((Date.now() - t0) / 1000).toFixed(0)}s`);
})().catch(e => { console.error(e); process.exit(1); });
