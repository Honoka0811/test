#!/usr/bin/env bash
# 映像(capture.js の出力)と音声(narrate.py の mix.wav)を合成し、-14 LUFS に正規化して最終版を書き出す
set -euo pipefail
cd "$(dirname "$0")"
V=output/guillotine_video.mp4; A=output/mix.wav; OUT=output/guillotine_short.mp4
M=$(ffmpeg -hide_banner -i "$A" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$V" -i "$A" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "wrote $OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 "$OUT"
