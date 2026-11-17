#!/usr/bin/env bash
# 必要なもの(フォント・VOICEVOX)を取得する。VOICEVOX 一式は /home/user/vv に置く(narrate.py の既定パス)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts/noto-sans-jp && (cd fonts && npm pack @fontsource/noto-sans-jp >/dev/null && tar xzf fontsource-noto-sans-jp-*.tgz -C noto-sans-jp --strip-components=1 && rm fontsource-noto-sans-jp-*.tgz)
VV=${VV:-/home/user/vv}; mkdir -p "$VV/ort" "$VV/vvms"
curl -sSL https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C "$VV/ort"
curl -sSL -o "$VV/vvms/0.vvm" https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.16.0/0.vvm
pip install -q pyopenjtalk numpy https://github.com/VOICEVOX/voicevox_core/releases/download/0.17.1/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
