#!/usr/bin/env bash
# 無音動画 + ミックス音声を合成し、YouTube 向けに -14 LUFS へ正規化して upload/ に書き出す
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p upload
ffmpeg -y -loglevel error -i output/video_silent.mp4 -i output/mix.wav \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11" -ar 48000 -ac 2 \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  upload/paper_fold_moon.mp4
cp output/subtitles_ja.srt upload/
node capture.js --stills 4.7 >/dev/null
ffmpeg -y -loglevel error -i output/stills/t004.70.png -q:v 2 upload/thumbnail.jpg
echo "upload/paper_fold_moon.mp4"
