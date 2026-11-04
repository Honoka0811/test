#!/usr/bin/env bash
# 映像(output/video_silent.mp4)と音声(output/mix.wav)を合成し、アップロード用一式を upload/ に書き出す
# 音量は -14 LUFS(YouTube 基準)に 2 パスで正規化、ステレオ AAC
set -euo pipefail
cd "$(dirname "$0")"
OUT=upload; mkdir -p "$OUT"
DST="$OUT/trump_japan_top5_final.mp4"

M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,volume=1.5dB" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "$DST"

cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 "$OUT/thumbnail.jpg"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 "$DST"
ffmpeg -hide_banner -i "$DST" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
