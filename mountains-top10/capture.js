// render.html を 1 フレームずつ撮影し、ffmpeg で mp4 (無音) にエンコードする
// 使い方: node capture.js [出力mp4]            … 動画を書き出す
//         node capture.js --stills 1.5 9 ...   … 指定秒のフレームを output/stills/ に PNG で保存(確認用)
// シーンの尺は output/timing.json(narrate.py がナレーション長から算出)があればそれを、無ければ scenes.json の dur を使う
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

function loadData() {
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'scenes.json'), 'utf8'));
  const tf = path.join(__dirname, 'output', 'timing.json');
  if (fs.existsSync(tf)) {
    const timing = JSON.parse(fs.readFileSync(tf, 'utf8'));
    data.scenes.forEach(s => { if (timing[s.id]) s.dur = timing[s.id]; });
    console.log('timing: output/timing.json');
  } else console.log('timing: scenes.json の既定値');
  return data;
}

(async () => {
  const args = process.argv.slice(2);
  const stills = args[0] === '--stills';
  const out = stills ? null : (args[0] || path.join(__dirname, 'output', 'mountains_top10_silent.mp4'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const data = loadData();
  await page.addInitScript(d => { window.DATA = d; }, data);
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => document.fonts.ready);
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  const grab = async t => Buffer.from((await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

  if (stills) {
    const dir = path.join(__dirname, 'output', 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of args.slice(1)) { const f = path.join(dir, `t${String(s).padStart(5, '0')}.png`); fs.writeFileSync(f, await grab(parseFloat(s))); console.log('wrote', f); }
    await browser.close(); return;
  }
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const total = Math.round(FPS * DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log('wrote', out, `(${DURATION.toFixed(2)}s)`);
})().catch(e => { console.error(e); process.exit(1); });
