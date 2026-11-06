#!/usr/bin/env bash
# アップロード用の最終書き出し: 音量を -14 LUFS(YouTube 基準)に正規化し、サムネイル・字幕をまとめる
set -euo pipefail
cd "$(dirname "$0")"
SRC=output/nobel_foundation_assets.mp4
OUT=upload
mkdir -p "$OUT"
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$OUT/nobel_foundation_assets_final.mp4"
cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
node thumbnail.js "$OUT/thumbnail.png"
ffmpeg -y -hide_banner -loglevel error -i "$OUT/thumbnail.png" -q:v 2 "$OUT/thumbnail.jpg" && rm "$OUT/thumbnail.png"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 "$OUT/nobel_foundation_assets_final.mp4"
ffmpeg -hide_banner -i "$OUT/nobel_foundation_assets_final.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
