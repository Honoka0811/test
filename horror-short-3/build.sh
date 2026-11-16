#!/usr/bin/env bash
# 一括ビルド: ナレーション → BGM/効果音ミックス → 映像 → 音量正規化(-14 LUFS)して合成
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
python3 sound.py
node capture.js
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/silent.mp4 -i output/mix.wav \
  -c:v libx264 -preset slow -crf 23 -maxrate 5M -bufsize 10M -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,volume=-0.5dB,alimiter=limit=0.84:attack=2:release=50:level=false" \
  -ar 48000 -ac 2 -c:a aac -b:a 192k -shortest -movflags +faststart output/sleep_app_recording.mp4
ffmpeg -y -loglevel error -ss 50.0 -i output/sleep_app_recording.mp4 -frames:v 1 -q:v 2 output/thumbnail.jpg
echo "wrote output/sleep_app_recording.mp4"
