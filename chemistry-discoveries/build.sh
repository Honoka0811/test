#!/usr/bin/env bash
# 一括生成: ナレーション → 映像 → BGM ミックス → サムネイル
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output
python3 narrate.py          # output/narration.wav, timeline.js, output/subtitles_ja.srt
node capture.js             # output/video_silent.mp4
python3 mix.py              # output/bgm.wav, output/mix.wav, output/chemistry_discoveries.mp4
node -e "
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + process.cwd() + '/render.html'); await p.evaluate(() => document.fonts.ready);
  await p.evaluate(() => window.render(2.6)); await p.screenshot({ path: 'output/thumbnail.png' }); await b.close(); })();"
ffmpeg -y -loglevel error -i output/thumbnail.png -q:v 2 output/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,channels:format=duration,size -of default=nw=1 output/chemistry_discoveries.mp4
