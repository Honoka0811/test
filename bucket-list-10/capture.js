// render.html を 1 フレームずつ撮影し、ffmpeg で mp4(無音)にエンコードする
// 使い方: node capture.js [出力パス]        プレビュー: node capture.js --stills 秒,秒,... [出力ディレクトリ]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

// フォントを読み込めるようローカル HTTP サーバーで配信する
function serve(dir) {
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf' };
  const srv = http.createServer((req, res) => {
    const f = path.join(dir, decodeURIComponent(req.url.split('?')[0]));
    if (!f.startsWith(dir) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(r => srv.listen(0, '127.0.0.1', () => r(srv)));
}

(async () => {
  const srv = await serve(__dirname);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${srv.address().port}/render.html`);
  await page.evaluate(async () => { await Promise.all([...document.fonts].map(f => f.load())); await document.fonts.ready; });
  const shot = (t, type = 'png') => page.evaluate(([t, type]) => { window.render(t); return document.getElementById('c').toDataURL('image/' + type, 0.95); }, [t, type])
    .then(u => Buffer.from(u.split(',')[1], 'base64'));

  if (process.argv[2] === '--stills') {
    const dir = process.argv[4] || path.join(__dirname, 'output', 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const t of process.argv[3].split(',').map(Number)) fs.writeFileSync(path.join(dir, `t${t.toFixed(2)}.png`), await shot(t));
  } else {
    const out = process.argv[2] || path.join(__dirname, 'output', 'video.mp4');
    fs.mkdirSync(path.dirname(out), { recursive: true });
    const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
    const total = Math.round(FPS * DURATION);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
    ff.stderr.on('data', d => process.stderr.write(d));
    const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
    const t0 = Date.now();
    for (let i = 0; i < total; i++) {
      const buf = await shot(i / FPS, 'jpeg');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    }
    ff.stdin.end();
    await done;
    console.log('wrote', out);
  }
  await browser.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
