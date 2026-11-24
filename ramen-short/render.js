// Renders short.html frame-by-frame and encodes a 1080x1920 MP4 with ffmpeg.
// Usage: node render.js [out.mp4] [--preview t1,t2,...]
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");

const FPS = 30;
const args = process.argv.slice(2);
const previewIdx = args.indexOf("--preview");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.resolve(__dirname, "short.html"));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);

  if (previewIdx >= 0) {
    for (const t of args[previewIdx + 1].split(",").map(Number)) {
      await page.evaluate(t => render(t), t);
      await page.screenshot({ path: path.join(args[previewIdx + 2] || ".", `preview_${t}.png`) });
    }
    await browser.close();
    return;
  }

  const out = args[0] || path.join(__dirname, "ramen_ranking_short.mp4");
  const total = await page.evaluate(() => window.TOTAL);
  const frames = Math.ceil(total * FPS);
  const ff = spawn("ffmpeg", ["-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
    "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });

  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => render(t), f / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (f % 150 === 0) console.log(`frame ${f}/${frames}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on("close", r));
  await browser.close();
  console.log("done:", out);
})();
