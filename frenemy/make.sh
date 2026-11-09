#!/usr/bin/env bash
# 一括生成: ナレーション → 映像 → BGMミックス → サムネイル
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py          # output/narration.wav, timeline.js, output/subtitles_ja.srt
node capture.js             # output/frenemy_video.mp4(無音)
python3 mix.py              # output/frenemy_narrated.mp4(完成版)
ffmpeg -y -loglevel error -ss 5.6 -i output/frenemy_video.mp4 -frames:v 1 -q:v 2 output/thumbnail.jpg
echo done
