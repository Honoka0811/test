#!/usr/bin/env bash
# 再生成に必要な外部素材を取得する(フォントのみ。BGM と地図データはリポジトリに同梱)
set -euo pipefail
cd "$(dirname "$0")/assets"
[ -f NotoSerifJP.ttf ] || curl -sSL -o NotoSerifJP.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifjp/NotoSerifJP%5Bwght%5D.ttf"
echo "assets ready"
