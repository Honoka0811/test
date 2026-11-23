#!/usr/bin/env bash
# 「午前2時のノック」を一式ビルドする: 音声 → 映像 → サムネイル → 合成
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output

python3 audio.py                 # output/mix.wav, timeline.json, subtitles_ja.srt
node capture.js                  # output/video_silent.mp4
node capture.js --thumb          # output/thumbnail.png

OUT=output/gozen2ji_knock.mp4
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -shortest -movflags +faststart "$OUT"
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 output/thumbnail.jpg

echo "wrote $OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT"
ffmpeg -hide_banner -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
