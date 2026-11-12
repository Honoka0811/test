#!/usr/bin/env bash
# 一括ビルド: ナレーション合成 → 映像レンダリング → BGMミックス → サムネイル
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py                     # output/narration.wav, timeline.json(.js), subtitles_ja.srt
node capture.js                        # output/video_silent.mp4
python3 mix.py                         # output/perfumer_short.mp4(-14 LUFS, ステレオ)
node capture.js --stills 5.5           # サムネイル用の静止画
ffmpeg -y -loglevel error -i output/stills/t5.5.png -q:v 2 output/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 output/perfumer_short.mp4
