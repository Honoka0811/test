#!/usr/bin/env bash
# 一括生成: ナレーション → 映像 → ミックス → アップロード用書き出し
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
node capture.js
python3 mix.py
./export_upload.sh
