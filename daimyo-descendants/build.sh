#!/usr/bin/env bash
# 一括ビルド: ナレーション合成 → 映像撮影 → BGM ミックス → サムネイル
#   ./build.sh            VOICEVOX(四国めたん)で完成版を作る
#   ./build.sh --preview  音声なしで尺を見積もり、BGM だけのプレビュー版を作る
set -euo pipefail
cd "$(dirname "$0")"
[ -f fonts/ShipporiMinchoB1-ExtraBold.ttf ] || ./fetch_fonts.sh
if [ "${1:-}" = "--preview" ]; then
  python3 narrate.py --estimate
else
  python3 narrate.py
fi
node capture.js
python3 mix.py
node capture.js --thumb
ls -la output/*.mp4 output/thumbnail.png
