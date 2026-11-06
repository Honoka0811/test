// 指定した時刻のフレームを PNG で書き出す(レイアウト確認用)  node snap.js 出力dir t1 t2 ...
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const [dir, ...ts] = process.argv.slice(2); fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'render.html')); await p.evaluate(() => document.fonts.ready);
  for (const t of ts) {
    const u = await p.evaluate(t => { window.render(+t); return document.getElementById('c').toDataURL('image/png'); }, t);
    fs.writeFileSync(path.join(dir, `f_${t}.png`), Buffer.from(u.split(',')[1], 'base64'));
  }
  await b.close();
})();
