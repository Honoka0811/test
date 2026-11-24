// Renders short.html frame-by-frame, mixes in the narration WAVs, and encodes a 1080x1920 MP4.
// Prereqs: photos/credits.json, audio/*.wav + audio/durations.json (run narration.py first).
// Usage: node render.js [out.mp4]            full render
//        node render.js --preview t1,t2 DIR   still frames for checking
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const FPS = 30;
const args = process.argv.slice(2);
const previewIdx = args.indexOf("--preview");
const here = p => path.join(__dirname, p);

function run(cmd, argv) {
  return new Promise((res, rej) => {
    const p = spawn(cmd, argv, { stdio: ["ignore", "inherit", "inherit"] });
    p.on("close", c => (c === 0 ? res() : rej(new Error(`${cmd} exited ${c}`))));
  });
}

(async () => {
  const credits = JSON.parse(fs.readFileSync(here("photos/credits.json"), "utf8"));
  const durs = JSON.parse(fs.readFileSync(here("audio/durations.json"), "utf8"));

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(([c, d]) => { window.CREDITS = c; window.DURS = d; }, [credits, durs]);
  await page.goto("file://" + here("short.html"));
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
  });
  await page.waitForTimeout(500);

  if (previewIdx >= 0) {
    const dir = args[previewIdx + 2] || ".";
    for (const t of args[previewIdx + 1].split(",").map(Number)) {
      await page.evaluate(t => render(t), t);
      await page.screenshot({ path: path.join(dir, `preview_${t}.png`) });
    }
    console.log("total", await page.evaluate(() => window.TOTAL));
    await browser.close();
    return;
  }

  const out = args[0] || here("ramen_ranking_short.mp4");
  const silent = out.replace(/\.mp4$/, ".video.mp4");
  const total = await page.evaluate(() => window.TOTAL);
  const narration = await page.evaluate(() => window.NARRATION);
  const frames = Math.ceil(total * FPS);

  // 1) video frames -> silent mp4
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20", silent], { stdio: ["pipe", "inherit", "inherit"] });
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => render(t), f / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (f % 300 === 0) console.log(`frame ${f}/${frames}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on("close", r));
  await browser.close();

  // 2) place each narration clip at its scene's start and mux
  const inputs = [], filters = [];
  narration.forEach((n, i) => {
    inputs.push("-i", here(`audio/${n.key}.wav`));
    const ms = Math.round(n.at * 1000);
    filters.push(`[${i + 1}:a]aresample=48000,adelay=${ms}|${ms}[a${i}]`);
  });
  const mix = narration.map((_, i) => `[a${i}]`).join("") +
    `amix=inputs=${narration.length}:normalize=0,apad,atrim=0:${total.toFixed(3)},loudnorm=I=-14:TP=-1.5:LRA=11[aout]`;
  await run("ffmpeg", ["-y", "-loglevel", "error", "-i", silent, ...inputs,
    "-filter_complex", [...filters, mix].join(";"), "-map", "0:v", "-map", "[aout]",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out]);
  fs.unlinkSync(silent);
  console.log("done:", out, `(${total.toFixed(1)}s)`);
})();
