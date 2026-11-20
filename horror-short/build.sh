#!/usr/bin/env bash
# Builds horror_short.mp4 (1080x1920, 30fps) from timeline.json
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
[ "${SKIP_RENDER:-}" = 1 ] || node render.js
ffmpeg -v error -y -framerate 30 -i frames/%05d.jpg -i audio.wav \
  -vf "noise=c0s=9:c0f=t,format=yuv420p" \
  -c:v libx264 -preset slow -crf 21 -maxrate 9M -bufsize 18M -c:a aac -b:a 192k -movflags +faststart -shortest horror_short.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 horror_short.mp4
