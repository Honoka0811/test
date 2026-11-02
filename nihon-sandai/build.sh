#!/usr/bin/env bash
# 一括ビルド: ナレーション合成 → フレーム撮影 → 音声合成 → アップロード用書き出し
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py                 # 音声・字幕・credit.txt(動画が無ければ音声のみ)
node capture.js                    # output/nihon_sandai.mp4(無音版)
python3 narrate.py                 # output/nihon_sandai_narrated.mp4
./export_upload.sh                 # upload/
