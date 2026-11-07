#!/usr/bin/env bash
# 一括ビルド: ナレーション合成(VOICEVOX 四国めたん) → 映像撮影 → BGM/効果音ミックス → カバー画像
set -euo pipefail
cd "$(dirname "$0")"
[ -f fonts/ShipporiMinchoB1-ExtraBold.ttf ] || ./fetch_fonts.sh
python3 narrate.py
node capture.js
python3 mix.py
node capture.js --thumb
ls -la output/sleep_short.mp4 output/thumbnail.png
