#!/usr/bin/env bash
# ナレーション+BGM → 映像撮影 → 合成 → -14 LUFS 正規化 まで一括で行う
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py                       # output/mix.wav, output/subs.js, output/subtitles_ja.srt
node capture.js output/queue_proxy_silent.mp4
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/queue_proxy_silent.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart output/queue_proxy_short.mp4
echo "wrote output/queue_proxy_short.mp4"
