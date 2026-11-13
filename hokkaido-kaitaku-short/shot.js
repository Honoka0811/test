// 確認用: node shot.js 1.5 9 13 ... → out/preview/t_*.jpg と contact.jpg
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const dir = path.join(__dirname, 'out', 'preview'); fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('console', m => console.log('console:', m.text())); p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + path.join(__dirname, 'render.html'));
  await p.evaluate(async () => { window.render(0); await document.fonts.load('800 10px Mincho'); await document.fonts.load('900 10px Sans'); await document.fonts.load('700 10px Sans'); await document.fonts.load('500 10px Sans'); await document.fonts.ready; });
  for (const t of process.argv.slice(2)) { await p.evaluate(t => window.render(t), parseFloat(t)); await p.screenshot({ path: path.join(dir, `t_${t}.jpg`), quality: 85, clip: { x: 0, y: 0, width: 1080, height: 1920 } }); }
  await b.close();
})();
