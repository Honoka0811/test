// scene.html を timeline.json の尺でフレーム撮影し ffmpeg で mp4 化。output/mix.wav があればナレーション付き版も作る。
//   node capture.js
const { chromium } = require('playwright');
const { spawn, spawnSync } = require('child_process');
const path = require('path'); const fs = require('fs');
(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.json')));
  const fps = 30, DUR = tl.sc[tl.sc.length - 1][1], N = Math.ceil(fps * DUR);
  const out = path.join(__dirname, 'output'); fs.mkdirSync(out, { recursive: true });
  const silent = path.join(out, 'ai_power_datacenter.mp4');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.resolve(__dirname, 'scene.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(sc => window.setTimeline(sc), tl.sc);
  await page.waitForTimeout(300);
  // サムネイル(フックのカット)
  await page.evaluate(() => window.setT(2.0));
  await page.screenshot({ path: path.join(out, 'thumbnail.png'), type: 'png' });
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-movflags', '+faststart', silent], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = 0; i < N; i++) {
    await page.evaluate(t => window.setT(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await browser.close();
  console.log(`wrote ${silent} (${N} frames, ${((Date.now() - t0) / 1000).toFixed(1)}s)`);
  const mix = path.join(out, 'mix.wav');
  if (fs.existsSync(mix)) {
    const dst = path.join(out, 'ai_power_datacenter_narrated.mp4');
    spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-i', mix, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', dst], { stdio: 'inherit' });
    console.log('wrote', dst);
  }
})();
