#!/usr/bin/env bash
# 一括生成: ナレーション+BGM → 映像(字幕焼き込み) → 合成・-14 LUFS 正規化 → upload/
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output upload
python3 narrate.py
node capture.js output/video_silent.mp4
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart upload/haber_bosch_short.mp4
cp output/subtitles_ja.srt upload/
node capture.js --stills 1.6 output/thumb && ffmpeg -y -loglevel error -i output/thumb/t001.6.png -q:v 2 upload/thumbnail.jpg 2>/dev/null \
  || ffmpeg -y -loglevel error -i "$(ls output/thumb/*.png | head -1)" -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,channels:format=duration -of default=nw=1 upload/haber_bosch_short.mp4
ffmpeg -hide_banner -i upload/haber_bosch_short.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
