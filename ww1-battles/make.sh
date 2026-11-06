#!/usr/bin/env bash
# 一括生成: ナレーション合成 → 映像の書き出し → BGM ミックス → アップロード用書き出し
set -euo pipefail
cd "$(dirname "$0")"
./fetch_assets.sh
python3 narrate.py                   # output/narration.wav, timings.json, subtitles_ja.srt
node capture.js                      # output/video_silent.mp4(timings.json に合わせて描画)
python3 mix.py                       # output/ww1_battles.mp4
THUMB=1 node capture.js --stills 4.5 && mv output/still_4_5.png output/thumbnail.png
./export_upload.sh                   # upload/
