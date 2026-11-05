#!/usr/bin/env bash
# 全工程: ナレーション合成 → 映像書き出し → BGM合成 → ミックス・最終mp4 → サムネイル
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py          # output/narration.wav, timings.js, output/subtitles_ja.srt
node capture.js             # output/video_silent.mp4(と BGM 同期用の output/sync.json)
python3 bgm.py              # output/bgm.wav
python3 mix.py              # output/jr_hokkaido_peak_network.mp4
node capture.js --stills 2.8 && ffmpeg -y -loglevel error -i output/stills/t2.8.png -q:v 2 output/thumbnail.jpg
echo done
