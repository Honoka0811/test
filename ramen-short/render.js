// Renders short.html frame-by-frame, mixes narration + SFX + BGM (ducked under the voice), and encodes a 1080x1920 MP4.
// Prereqs: photos/credits.json, audio/*.wav + durations.json + captions.json (narration.py), audio/sfx/*.wav (music.py).
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
const readJSON = p => JSON.parse(fs.readFileSync(here(p), "utf8"));

function run(cmd, argv) {
  return new Promise((res, rej) => {
    const p = spawn(cmd, argv, { stdio: ["ignore", "inherit", "inherit"] });
    p.on("close", c => (c === 0 ? res() : rej(new Error(`${cmd} exited ${c}`))));
  });
}

(async () => {
  const inject = [readJSON("photos/credits.json"), readJSON("audio/durations.json"), readJSON("audio/captions.json")];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(([c, d, cap]) => { window.CREDITS = c; window.DURS = d; window.CAPS = cap; }, inject);
  await page.goto("file://" + here("short.html"));
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
  });
  await page.waitForTimeout(500);
  const total = await page.evaluate(() => window.TOTAL);

  if (previewIdx >= 0) {
    const dir = args[previewIdx + 2] || ".";
    for (const t of args[previewIdx + 1].split(",").map(Number)) {
      await page.evaluate(t => render(t), t);
      await page.screenshot({ path: path.join(dir, `preview_${t}.png`) });
    }
    console.log("total", total, JSON.stringify(await page.evaluate(() => window.VOICE)));
    await browser.close();
    return;
  }

  const out = args[0] || here("ramen_ranking_short.mp4");
  const silent = out.replace(/\.mp4$/, ".video.mp4");
  const voice = await page.evaluate(() => window.VOICE);
  const sfx = await page.evaluate(() => window.SFX);
  const frames = Math.ceil(total * FPS);

  // 1) video frames -> silent mp4
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "19", silent], { stdio: ["pipe", "inherit", "inherit"] });
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => render(t), f / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (f % 300 === 0) console.log(`frame ${f}/${frames}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on("close", r));
  await browser.close();

  // 2) audio: voice + sfx + ducked bgm
  const inputs = [], filters = [];
  let idx = 1;
  const place = (file, at, label, gain = 1) => {
    inputs.push("-i", file);
    const ms = Math.max(0, Math.round(at * 1000));
    filters.push(`[${idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume=${gain},adelay=${ms}|${ms}[${label}]`);
    idx++;
    return `[${label}]`;
  };
  const v = voice.map((n, i) => place(here(`audio/${n.key}.wav`), n.at, `v${i}`, 1.0));
  const SFX_GAIN = { whoosh: 0.35, pop: 0.45, drumroll: 0.6, reveal: 0.6, ding: 0.5 };
  const s = sfx.map((e, i) => place(here(`audio/sfx/${e.name}.wav`), e.at, `s${i}`, SFX_GAIN[e.name] || 0.4));
  const bgm = place(here("audio/sfx/bgm.wav"), 0, "bgraw", 1.0);
  const T = total.toFixed(3);
  filters.push(
    `${v.join("")}amix=inputs=${v.length}:normalize=0,apad,atrim=0:${T},asplit=2[vo][vokey]`,
    `${s.join("")}amix=inputs=${s.length}:normalize=0,apad,atrim=0:${T}[fx]`,
    `${bgm}atrim=0:${T},volume=0.20,afade=t=in:d=0.2,afade=t=out:st=${(total - 1.2).toFixed(2)}:d=1.2[bg]`,
    `[bg][vokey]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=350[bgd]`,
    `[vo][fx][bgd]amix=inputs=3:normalize=0,alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=9[aout]`
  );
  await run("ffmpeg", ["-y", "-loglevel", "error", "-i", silent, ...inputs,
    "-filter_complex", filters.join(";"), "-map", "0:v", "-map", "[aout]",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", T, "-movflags", "+faststart", out]);
  fs.unlinkSync(silent);
  console.log("done:", out, `(${total.toFixed(1)}s)`);
})();
