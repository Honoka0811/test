// 指定した時刻のフレームを PNG で書き出す(確認用)。使い方: node snap.js 出力dir t1 t2 ...  / node snap.js --thumb 出力png
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('pageerror', e); process.exitCode = 1; });
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(() => window.READY);
  const grab = async () => Buffer.from((await page.evaluate(() => document.getElementById('c').toDataURL('image/png'))).split(',')[1], 'base64');
  if (args[0] === '--thumb') {
    await page.evaluate(() => renderThumb());
    fs.writeFileSync(args[1], await grab());
  } else {
    fs.mkdirSync(args[0], { recursive: true });
    for (const t of args.slice(1)) {
      await page.evaluate(t => render(t), +t);
      fs.writeFileSync(path.join(args[0], `t${(+t).toFixed(2).padStart(6, '0')}.png`), await grab());
    }
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
