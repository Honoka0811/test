#!/usr/bin/env bash
# 一括生成: ナレーション → 映像 → BGMミックス
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output
python3 narrate.py
node capture.js
python3 mix.py
