#!/usr/bin/env bash
# アップロード用の最終書き出し: -14 LUFS(YouTube 基準)に正規化、字幕・サムネイルをまとめる
set -euo pipefail
cd "$(dirname "$0")"
SRC=output/showa_best5.mp4; OUT=upload; mkdir -p "$OUT"
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$OUT/showa_best5_final.mp4"
cp output/subtitles_ja.srt "$OUT/"
node capture.js --stills 6.3 && ffmpeg -y -loglevel error -i output/still_6.3.png -q:v 2 "$OUT/thumbnail.jpg"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 "$OUT/showa_best5_final.mp4"
ffmpeg -hide_banner -i "$OUT/showa_best5_final.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):"
