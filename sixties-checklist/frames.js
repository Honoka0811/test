// 指定した時刻のフレームを PNG で書き出す(確認用)  使い方: node frames.js 出力dir t1 t2 ...
const { chromium } = require('playwright');
const path = require('path'); const fs = require('fs');
(async () => {
  const dir = process.argv[2]; fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('console', m => console.log('[page]', m.text())); p.on('pageerror', e => console.log('[pageerror]', e.message));
  await p.goto('file://' + path.join(__dirname, 'render.html'));
  await p.evaluate(() => window.ready);
  for (const ts of process.argv.slice(3)) {
    const t = parseFloat(ts);
    const d = await p.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    fs.writeFileSync(path.join(dir, `f_${ts.replace('.', '_')}.png`), Buffer.from(d.split(',')[1], 'base64'));
  }
  await b.close(); console.log('ok');
})().catch(e => { console.error(e); process.exit(1); });
