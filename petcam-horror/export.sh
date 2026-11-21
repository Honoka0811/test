#!/usr/bin/env bash
# 無音の映像(capture.js)と音声(sound.py)を合成し、アップロード用に -14 LUFS へ正規化して書き出す
set -euo pipefail
cd "$(dirname "$0")"
OUT=upload
mkdir -p "$OUT"
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -c:v libx264 -crf 23 -preset medium -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,alimiter=limit=0.84:level=false" \
  -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT/petcam_horror_final.mp4"
cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
# サムネイル: テレビの反射に男が映るフレーム
ffmpeg -y -hide_banner -loglevel error -ss "$(python3 -I -c "import json;s={x['id']:x for x in json.load(open('output/timeline.json'))['scenes']};print(s['reveal']['end']-0.8)")" \
  -i output/video_silent.mp4 -frames:v 1 -q:v 2 "$OUT/thumbnail.jpg"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT/petcam_horror_final.mp4"
ffmpeg -hide_banner -i "$OUT/petcam_horror_final.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
