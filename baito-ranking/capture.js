// render.html を 1 フレームずつ撮影し、ffmpeg で無音の mp4 にエンコードする
// 使い方:
//   node capture.js                     … output/video_silent.mp4 を書き出す
//   node capture.js --stills 1.5 9 20   … 指定秒のフレームを output/stills/*.png に保存(確認用)
//   node capture.js --thumb 2.6         … 字幕なしのフレームを output/thumbnail.png に保存
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const ROOT = __dirname;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.json': 'application/json' };

function serve() {
  // file:// だと SVG アイコンを描いた canvas が toDataURL できない(tainted)ので、ローカルで配信する
  const srv = http.createServer((req, res) => {
    const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(res);
  });
  return new Promise(r => srv.listen(0, '127.0.0.1', () => r(srv)));
}

async function frame(page, t, opt = {}) {
  const url = await page.evaluate(([t, opt]) => { window.render(t, opt); return document.getElementById('c').toDataURL('image/png'); }, [t, opt]);
  return Buffer.from(url.split(',')[1], 'base64');
}

(async () => {
  const args = process.argv.slice(2);
  const srv = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('pageerror:', e.message));
  await page.goto(`http://127.0.0.1:${srv.address().port}/render.html`);
  await page.evaluate(() => window.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));

  if (args[0] === '--stills' || args[0] === '--thumb') {
    const dir = path.join(ROOT, 'output', args[0] === '--thumb' ? '' : 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of args.slice(1)) {
      const t = parseFloat(s);
      const out = args[0] === '--thumb' ? path.join(dir, 'thumbnail.png') : path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
      fs.writeFileSync(out, await frame(page, t, { noSub: args[0] === '--thumb' }));
      console.log('wrote', out);
    }
  } else {
    const out = path.join(ROOT, 'output', 'video_silent.mp4');
    const total = Math.round(FPS * DURATION);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out]);
    ff.stderr.on('data', d => process.stderr.write(d));
    const done = new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))));
    const t0 = Date.now();
    for (let i = 0; i < total; i++) {
      const buf = await frame(page, i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    }
    ff.stdin.end();
    await done;
    console.log('wrote', out);
  }
  await browser.close();
  srv.close();
})().catch(e => { console.error(e); process.exit(1); });
