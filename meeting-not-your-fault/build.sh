#!/usr/bin/env bash
# 一式を再生成する: フォント取得 → ナレーション → 映像 → BGMミックス
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts output
[ -f fonts/MPLUSRounded1c-Medium.ttf ] || curl -sSLf -o fonts/MPLUSRounded1c-Medium.ttf https://fonts.gstatic.com/s/mplusrounded1c/v22/VdGBAYIAV6gnpUpoWwNkYvrugw9RuM1y55sK.ttf
[ -f fonts/MPLUSRounded1c-ExtraBold.ttf ] || curl -sSLf -o fonts/MPLUSRounded1c-ExtraBold.ttf https://fonts.gstatic.com/s/mplusrounded1c/v22/VdGBAYIAV6gnpUpoWwNkYvrugw9RuM0m4psK.ttf
python3 narrate.py     # output/narration.wav, timeline.js, output/subtitles_ja.srt
node capture.js        # output/video_silent.mp4
python3 mix.py         # output/tsutawaranai_anatadake_janai.mp4
ffmpeg -y -loglevel error -ss 63.5 -i output/tsutawaranai_anatadake_janai.mp4 -frames:v 1 -q:v 2 output/thumbnail.jpg
