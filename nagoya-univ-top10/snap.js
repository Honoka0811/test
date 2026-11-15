// 指定時刻のフレームを PNG で保存: node snap.js 1.5 10 20 ...
const { chromium } = require('playwright');
const path = require('path'); const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('console', m => console.log('page:', m.text())); p.on('pageerror', e => console.log('err:', e.message));
  await p.goto('file://' + path.join(__dirname, 'render.html'));
  await p.waitForFunction(() => window.READY);
  for (const t of process.argv.slice(2)) {
    const d = await p.evaluate(t => { render(+t); return document.getElementById('c').toDataURL('image/png'); }, t);
    fs.writeFileSync(path.join(__dirname, 'preview', `t${t}.png`), Buffer.from(d.split(',')[1], 'base64'));
  }
  await b.close();
})();
