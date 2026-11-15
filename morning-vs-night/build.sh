#!/usr/bin/env bash
# 一括生成: ナレーション+BGM → 映像 → 合成(-14 LUFS 正規化・ステレオAAC)
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
node capture.js output/video_silent.mp4
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart \
  output/morning_vs_night.mp4
node snapshot.js output 3.5 && mv output/f_3.5.png output/thumbnail.png
echo "wrote output/morning_vs_night.mp4"
