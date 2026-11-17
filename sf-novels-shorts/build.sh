#!/usr/bin/env bash
# 一括ビルド: ナレーション+BGM → 映像 → 音量正規化(-14 LUFS)して合成
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
node capture.js output/video_silent.mp4
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav \
  -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart \
  output/sf_novels_10_shorts.mp4
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 output/thumbnail.jpg
rm -f output/still_*.png output/sheet*.png
echo "wrote output/sf_novels_10_shorts.mp4"
