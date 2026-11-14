// 指定時刻の静止画を並べたコンタクトシートを作る(検品用)。
// 使い方: node tools/sheet.js "0.5,2.3,5" [出力png] [--cols 5] [--scale 0.4] [--ui 1]
//   --ui 1 で YouTube ショートの UI が重なるおおよその領域(上部・右のボタン列・下部)を赤く重ねる
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const args = process.argv.slice(2), opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args.splice(i, 2)[1] : d; };
  const cols = Number(opt('cols', 5)), scale = Number(opt('scale', 0.4)), ui = Number(opt('ui', 0));
  const times = args[0].split(',').map(Number), out = path.resolve(args[1] || 'build/sheet.png');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  await page.goto('file://' + path.resolve(__dirname, '..', 'render.html'));
  await page.evaluate(() => window.READY);
  const data = await page.evaluate(({ times, cols, scale, ui }) => {
    const w = Math.round(1080 * scale), h = Math.round(1920 * scale), rows = Math.ceil(times.length / cols);
    const s = document.createElement('canvas'); s.width = w * cols; s.height = h * rows;
    const g = s.getContext('2d'); g.imageSmoothingQuality = 'high';
    const ms = [];
    times.forEach((t, i) => {
      const t0 = performance.now(); window.render(t); ms.push(Math.round(performance.now() - t0));
      const x = (i % cols) * w, y = Math.floor(i / cols) * h;
      g.drawImage(document.getElementById('c'), x, y, w, h);
      if (ui) {            // ショートの UI がかぶる目安(非公式の実測値ベース): 上 0-200、右 900-1080(y 880-1560)、下 1560-1920
        g.fillStyle = 'rgba(255,0,0,0.22)';
        g.fillRect(x, y, w, 200 * scale); g.fillRect(x + 900 * scale, y + 880 * scale, 180 * scale, 680 * scale); g.fillRect(x, y + 1560 * scale, w, 360 * scale);
        g.strokeStyle = 'rgba(0,255,120,0.8)'; g.setLineDash([6, 6]); g.strokeRect(x + 60 * scale, y + 290 * scale, 820 * scale, 960 * scale); g.setLineDash([]);
      }
      g.fillStyle = 'rgba(0,0,0,0.7)'; g.fillRect(x, y, 92, 30); g.fillStyle = '#0f0'; g.font = '20px monospace'; g.fillText(t.toFixed(2) + 's', x + 6, y + 22);
      g.strokeStyle = '#444'; g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    });
    return { url: s.toDataURL('image/png'), ms };
  }, { times, cols, scale, ui });
  fs.writeFileSync(out, Buffer.from(data.url.split(',')[1], 'base64'));
  console.log('wrote', out, 'render ms:', data.ms.join(' '));
  if (errs.length) { console.error('PAGE ERRORS:\n' + errs.join('\n')); process.exitCode = 1; }
  await browser.close();
})();
