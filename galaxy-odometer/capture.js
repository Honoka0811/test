// render.html を 1 フレームずつ撮影して mp4(無音)にする。
// 複数ページで区間を分担して並列に撮り、最後に無劣化で連結する。
// 使い方: node capture.js [--workers 3] [--from 秒] [--to 秒] [--out build/video.mp4]
//         node capture.js --still 12.5 --out build/still.png   (1 枚だけ書き出し)
//         node capture.js --poster --out build/thumbnail.png   (サムネイル)
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 ? process.argv[i + 1] : def;
}

(async () => {
  const html = path.resolve(__dirname, arg('html', 'render.html'));
  const still = arg('still', null);
  const poster = process.argv.includes('--poster');
  const out = path.resolve(__dirname, arg('out', poster ? 'build/thumbnail.png' : still !== null ? 'build/still.png' : 'build/video.mp4'));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const browser = await chromium.launch({ args: ['--font-render-hinting=none', '--disable-lcd-text'] });
  const open = async () => {
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => { console.error('PAGE ERROR:', e.message); process.exitCode = 1; });
    page.on('console', m => { if (m.type() === 'error') console.error('console.error:', m.text()); });
    await page.goto('file://' + html);
    await page.evaluate(() => window.READY);
    return page;
  };
  const grab = (page, t) => page.evaluate((t) => {
    window.render(t);
    return document.getElementById('c').toDataURL('image/png');
  }, t);

  if (poster) {                                   // サムネイル: 冒頭の構図 + 大きい見出し
    const page = await open();
    const url = await page.evaluate(() => { window.renderPoster(); return document.getElementById('c').toDataURL('image/png'); });
    fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
    console.log('wrote', out);
    await browser.close();
    return;
  }
  if (still !== null) {
    const page = await open();
    const times = String(still).split(',').map(Number);
    for (const t of times) {
      const o = times.length > 1 ? out.replace(/\.png$/, `_${t.toFixed(2)}.png`) : out;
      fs.writeFileSync(o, Buffer.from((await grab(page, t)).split(',')[1], 'base64'));
      console.log('wrote', o);
    }
    await browser.close();
    return;
  }

  const probe = await open();
  const { FPS, DURATION } = await probe.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  await probe.close();
  const f0 = Math.round(Number(arg('from', 0)) * FPS);
  const f1 = Math.round(Number(arg('to', DURATION)) * FPS);
  const workers = Math.max(1, Number(arg('workers', 3)));
  const total = f1 - f0;
  const per = Math.ceil(total / workers);
  const tmp = out + '.parts';
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(tmp, { recursive: true });
  const t0 = Date.now();
  let done = 0;

  const parts = await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const a = f0 + w * per, b = Math.min(f1, a + per);
    if (a >= b) return null;
    const part = path.join(tmp, `part${String(w).padStart(2, '0')}.mp4`);
    const page = await open();
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
      '-c:v', 'libx264', '-crf', arg('crf', '18'), '-preset', arg('preset', 'slow'), '-tune', 'animation',
      '-g', String(FPS * 2), '-bf', '2',
      '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
      '-video_track_timescale', String(FPS * 256), part]);
    ff.stderr.on('data', d => process.stderr.write(d));
    const closed = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
    for (let i = a; i < b; i++) {
      const buf = Buffer.from((await grab(page, i / FPS)).split(',')[1], 'base64');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (++done % 300 === 0) console.log(`frame ${done}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    await closed;
    await page.close();
    return part;
  }));
  await browser.close();

  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, parts.filter(Boolean).map(p => `file '${p}'`).join('\n') + '\n');
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', out]);
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(`wrote ${out}  (${total} frames, ${((Date.now() - t0) / 1000).toFixed(0)}s)`);
})().catch(e => { console.error(e); process.exit(1); });
