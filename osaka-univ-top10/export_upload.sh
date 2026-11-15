#!/usr/bin/env bash
# アップロード用一式を upload/ に書き出す(最終mp4・字幕SRT・サムネイルJPG)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p upload
cp output/osaka_univ_top10.mp4 upload/osaka_univ_top10.mp4
cp output/subtitles_ja.srt upload/subtitles_ja.srt
node capture.js --stills 2.4 >/dev/null
ffmpeg -y -hide_banner -loglevel error -i output/stills/t2.4.png -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 upload/osaka_univ_top10.mp4
ffmpeg -hide_banner -i upload/osaka_univ_top10.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
