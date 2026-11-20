#!/usr/bin/env bash
# Builds one short (1080x1920, 30fps) from a cue file.
# usage: ./build.sh [cues.json] [out.mp4]   (defaults: timeline.json horror_short.mp4)
# A cue file may name its own "scene" (html), "audio" (py) and ffmpeg "vf" chain.
set -euo pipefail
cd "$(dirname "$0")"
export TIMELINE="$(realpath "${1:-timeline.json}")"
OUT="${2:-horror_short.mp4}"
get() { node -p "(require('$TIMELINE')['$1']) || '$2'"; }
python3 "$(get audio audio.py)"
[ "${SKIP_RENDER:-}" = 1 ] || node render.js
ffmpeg -v error -y -framerate 30 -i frames/%05d.jpg -i audio.wav \
  -vf "$(get vf 'noise=c0s=9:c0f=t,format=yuv420p')" \
  -c:v libx264 -preset slow -crf 21 -maxrate 9M -bufsize 18M -c:a aac -b:a 192k -movflags +faststart -shortest "$OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
