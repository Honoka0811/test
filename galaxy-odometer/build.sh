#!/usr/bin/env bash
# 台本(script.json)から完成動画までを一括で作る。
#   ./build.sh          全工程
#   ./build.sh audio    音声だけ作り直す(映像は撮り直さない)
set -euo pipefail
cd "$(dirname "$0")"
NAME=galaxy_odometer_short
mkdir -p build output upload

echo "== 1/5 ナレーション合成 → タイムライン"
python3 tts.py script.json
node tools/export_plan.js

echo "== 2/5 BGM・効果音・ミックス"
python3 mix.py

if [ "${1:-all}" != "audio" ]; then
  echo "== 3/5 映像を 1 フレームずつ撮影(60fps)"
  node capture.js --workers "${WORKERS:-3}" --out build/video.mp4
fi

echo "== 4/5 映像と音声を結合し、音量を -14 LUFS に正規化"
M=$(ffmpeg -hide_banner -i build/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i build/video.mp4 -i build/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ar 48000 -ac 2 -c:a aac -b:a 192k -shortest -movflags +faststart "output/$NAME.mp4"

echo "== 5/5 アップロード用一式(upload/)"
cp "output/$NAME.mp4" "upload/$NAME.mp4"
python3 tools/make_srt.py upload/subtitles_ja.srt
node capture.js --poster --out build/thumbnail.png
ffmpeg -y -hide_banner -loglevel error -i build/thumbnail.png -q:v 2 upload/thumbnail.jpg

ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "upload/$NAME.mp4"
ffmpeg -hide_banner -i "upload/$NAME.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
