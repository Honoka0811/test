#!/usr/bin/env bash
# 一括生成: ナレーション+BGM → 映像(字幕焼き込み) → 音声と合成 → -14 LUFS 正規化した最終mp4
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
node capture.js output/video_silent.mp4
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart output/sanoku_en_jiken.mp4
echo "wrote output/sanoku_en_jiken.mp4"
