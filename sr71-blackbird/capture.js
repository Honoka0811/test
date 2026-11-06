// render.html を 1 フレームずつ描いて ffmpeg で mp4(無音)にする
// 使い方:
//   node capture.js                      -> output/video_silent.mp4
//   node capture.js --stills 1,6,13 ...  -> output/stills/t_<秒>.png(確認用)
//   node capture.js --thumb              -> output/thumbnail.png
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const tl = JSON.parse(fs.readFileSync(path.join(__dirname, 'output', 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  // 使う文字すべてについてフォントのサブセットを読み込んでから描画する
  const ok = await page.evaluate(async (tl) => {
    const chars = document.documentElement.outerHTML + JSON.stringify(tl) + '0123456789,.+:%℃→';
    for (const f of ['400 64px "Dela Gothic One"', '700 64px "Noto Sans JP"', '900 64px "Noto Sans JP"']) await document.fonts.load(f, chars);
    await document.fonts.ready;
    window.init(tl);
    return ['400 64px "Dela Gothic One"', '900 64px "Noto Sans JP"'].map(f => document.fonts.check(f, '撃墜ゼロ'));
  }, tl);
  console.log('fonts loaded:', ok);
  const grab = async (expr) => Buffer.from((await page.evaluate(expr)).split(',')[1], 'base64');

  if (args[0] === '--thumb') {
    const out = path.join(__dirname, 'output', 'thumbnail.png');
    fs.writeFileSync(out, await grab(`(window.renderThumb(), document.getElementById('c').toDataURL('image/png'))`));
    console.log('wrote', out); await browser.close(); return;
  }
  if (args[0] === '--stills') {
    const dir = path.join(__dirname, 'output', 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const t of args[1].split(',').map(Number)) {
      fs.writeFileSync(path.join(dir, `t_${t.toFixed(2)}.png`), await grab(`(window.render(${t}), document.getElementById('c').toDataURL('image/png'))`));
    }
    console.log('wrote stills to', dir); await browser.close(); return;
  }

  const out = path.join(__dirname, 'output', 'video_silent.mp4');
  const FPS = 30, total = Math.round(tl.duration * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', '-preset', 'slow', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(`(window.render(${i / FPS}), document.getElementById('c').toDataURL('image/jpeg', 0.95))`);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out);
})().catch(e => { console.error(e); process.exit(1); });
