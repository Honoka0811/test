#!/bin/bash
# ナレーション合成 → BGM生成 → フレーム撮影 → 動画化 を一括実行する
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
python3 bgm.py
node capture.js
# BGMはナレーション中だけ自動で音量を下げる(サイドチェイン)
ffmpeg -y -loglevel error -framerate 30 -i output/frames/f%05d.jpg -i output/narration.wav -i output/bgm.wav \
  -filter_complex "[1:a]aformat=channel_layouts=stereo,asplit=2[nar][key];[2:a]volume=0.5[bgm];\
[bgm][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450[duck];\
[nar][duck]amix=inputs=2:normalize=0,volume=4.5dB,alimiter=limit=0.9[a]" \
  -map 0:v -map "[a]" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 192k -movflags +faststart -shortest output/detective_short.mp4
rm -rf output/frames
ffprobe -v error -show_entries format=duration,size -of default=nw=1 output/detective_short.mp4
