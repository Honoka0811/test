// render.html を 1フレームずつ描画して ffmpeg に流し、mix.wav と合わせて mp4 を作る。
// 使い方: node render.js <buildDir> <out.mp4> [--still t1,t2,...]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const B = path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3]);
const stillArg = process.argv.indexOf('--still');
const FPS = 30;

(async () => {
  fs.copyFileSync(path.join(__dirname, 'render.html'), path.join(B, 'render.html'));
  const TL = JSON.parse(fs.readFileSync(path.join(B, 'voice/timeline.json')));
  const CU = JSON.parse(fs.readFileSync(path.join(B, 'cues.json')));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error('PAGE ERROR', e));
  await page.addInitScript(([tl, cu]) => { window.__TL = tl; window.__CUES = cu; }, [TL, CU]);
  await page.goto('file://' + path.join(B, 'render.html'));
  await page.evaluate(() => window.ready);

  if (stillArg > 0) {
    for (const t of process.argv[stillArg + 1].split(',').map(Number)) {
      await page.evaluate((t) => window.render(t), t);
      await page.screenshot({ path: path.join(B, `still_${t}.png`) });
    }
    await browser.close();
    return;
  }

  const total = CU.total + 0.3;
  const n = Math.ceil(total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', path.join(B, 'mix.wav'),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-shortest', '-movflags', '+faststart', OUT], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    await page.evaluate((t) => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close();
  console.log('done', OUT);
})();
