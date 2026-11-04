// 指定時刻のフレームを PNG で書き出す(確認用): node snap.js 1.0 20.5 ...
const { chromium } = require('playwright');
const path = require('path'); const fs = require('fs');
(async () => {
  const dir = process.env.SNAP_DIR || path.join(__dirname, 'output', 'snaps'); fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('PAGEERROR', e.message));
  await p.goto('file://' + path.join(__dirname, 'render.html')); await p.evaluate(() => document.fonts.ready);
  for (const t of process.argv.slice(2)) {
    await p.evaluate(t => window.render(+t), t);
    await p.locator('#c').screenshot({ path: path.join(dir, `t${String(t).padStart(6, '0')}.png`) });
  }
  await b.close();
})();
