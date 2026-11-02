// Screenshot every *.html in the given directory at 1920x1080.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
(async () => {
  const dir = process.argv[2];
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.html')).sort();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  for (const f of files) {
    await page.goto('file://' + path.join(dir, f));
    await page.waitForTimeout(80);
    await page.screenshot({ path: path.join(dir, f.replace('.html', '.png')) });
  }
  await browser.close();
  console.log('rendered', files.length, 'frames');
})();
