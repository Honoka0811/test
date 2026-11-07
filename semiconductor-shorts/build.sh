#!/usr/bin/env bash
# ナレーション → 映像 → BGM/効果音ミックス → アップロード用一式、の順に全部作り直す
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
node capture.js
python3 audio.py
mkdir -p upload
cp output/semiconductor_short.mp4 upload/
cp output/subtitles_ja.srt upload/
node preview.js output 4.75 && ffmpeg -y -loglevel error -i output/f_004.75.png -q:v 2 upload/thumbnail.jpg && rm output/f_004.75.png
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 upload/semiconductor_short.mp4
