// 縦型ショート動画レンダラー
// video.html を Playwright で1フレームずつ描画し、ffmpeg で MP4 にまとめる。
// 使い方: node render.cjs [--preview]   (--preview は数フレームだけ PNG 出力)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const FPS = 30;
const DURATION = 63; // 秒。video.html の DURATION と合わせる
const W = 1080, H = 1920;
const OUT = path.join(__dirname, 'drone_short.mp4');
const PREVIEW_DIR = path.join(__dirname, 'preview');
const preview = process.argv.includes('--preview');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'video.html'));
  await page.evaluate(() => document.fonts.ready);

  if (preview) {
    fs.mkdirSync(PREVIEW_DIR, { recursive: true });
    const times = [1.5, 8.5, 15, 21.5, 28, 34.5, 41, 47.5, 55, 61.5];
    for (const t of times) {
      await page.evaluate(t => window.render(t), t);
      await page.screenshot({ path: path.join(PREVIEW_DIR, `t${t}.png`) });
    }
    await browser.close();
    console.log('preview written to', PREVIEW_DIR);
    return;
  }

  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-vcodec', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-r', String(FPS), '-movflags', '+faststart', OUT,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  const total = FPS * DURATION;
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    await page.evaluate(t => window.render(t), t);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % (FPS * 5) === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))));
  await browser.close();
  console.log('done:', OUT);
})().catch(e => { console.error(e); process.exit(1); });
