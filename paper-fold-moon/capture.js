// render.html を 1 フレームずつ描画して ffmpeg に流し、無音の mp4 を作る。
// 使い方: node capture.js                 → output/video_silent.mp4
//        node capture.js --stills 1.2 5 … → output/stills/*.png(確認用の静止画)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30;
const HERE = __dirname;
const OUT = path.join(HERE, 'output');

(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.addInitScript(() => { window.CAPTURE = true; });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.goto('file://' + path.join(HERE, 'render.html'));
  await page.evaluate(tl => window.init(tl), tl);
  await page.waitForFunction(() => window.READY === true);

  // 効果音のタイミングを bgm.py に渡す
  fs.writeFileSync(path.join(OUT, 'events.json'), JSON.stringify(await page.evaluate(() => window.getEvents()), null, 1));

  const grab = async t => {
    const url = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(url.split(',')[1], 'base64');
  };

  const si = process.argv.indexOf('--stills');
  if (si >= 0) {
    const dir = path.join(OUT, 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of process.argv.slice(si + 1)) {
      fs.writeFileSync(path.join(dir, `t${(+s).toFixed(2).padStart(6, '0')}.png`), await grab(+s));
    }
    await browser.close();
    return;
  }

  const frames = Math.round(tl.total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    path.join(OUT, 'video_silent.mp4')], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < frames; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${frames}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('done', frames, 'frames');
})();
