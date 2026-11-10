#!/usr/bin/env bash
# 一括生成: ナレーション → 映像 → BGMミックス → サムネイル
set -euo pipefail
cd "$(dirname "$0")"
python3 voice.py
node capture.js
python3 mix.py
python3 bgm.py "$(python3 -c "import json;print(json.load(open('output/timings.json'))['total'])")" output/bgm.wav
