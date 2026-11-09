// 指定時刻のフレームを PNG で書き出す(確認用) 使い方: node snap.js 出力dir t1 t2 ...
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const [dir, ...ts] = process.argv.slice(2);
  fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('pageerror', e));
  await p.goto('file://' + path.join(__dirname, 'render.html'));
  await p.evaluate(() => document.fonts.load('800 50px MPR').then(() => document.fonts.load('700 50px MPR')));
  for (const t of ts) {
    await p.evaluate(t => window.render(+t), t);
    await p.locator('#c').screenshot({ path: path.join(dir, `f_${t}.png`) });
  }
  await b.close();
})();
