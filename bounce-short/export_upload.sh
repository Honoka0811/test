#!/usr/bin/env bash
# アップロード用の最終書き出し: -14 LUFS(YouTube 基準)に正規化、ステレオ AAC、サムネイル JPG
set -euo pipefail
cd "$(dirname "$0")"
SRC=output/every_bounce_bigger.mp4
mkdir -p upload
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart upload/every_bounce_bigger_final.mp4
python3 thumbnail.py
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 upload/every_bounce_bigger_final.mp4
ffmpeg -hide_banner -i upload/every_bounce_bigger_final.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
