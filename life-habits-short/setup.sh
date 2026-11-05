#!/usr/bin/env bash
# 依存物の取得: VOICEVOX CORE(四国めたん)とフォント。既定の置き場所は ~/vv と ./fonts
set -euo pipefail
cd "$(dirname "$0")"
VV=${VOICEVOX_HOME:-$HOME/vv}
mkdir -p "$VV/vvms" "$VV/ort" fonts
WHL=voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
curl -sSfL -o "$VV/$WHL" https://github.com/VOICEVOX/voicevox_core/releases/download/0.17.1/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
curl -sSfL https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C "$VV/ort"
curl -sSfL -o "$VV/vvms/0.vvm" https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.16.3/0.vvm   # 四国めたん/ずんだもん ほか
pip install "$VV/$WHL" pyopenjtalk numpy scipy
G=https://raw.githubusercontent.com/google/fonts/main/ofl
for f in mplusrounded1c/MPLUSRounded1c-Black.ttf mplusrounded1c/MPLUSRounded1c-ExtraBold.ttf delagothicone/DelaGothicOne-Regular.ttf notocoloremoji/NotoColorEmoji-Regular.ttf; do
  curl -sSfL -o "fonts/$(basename $f)" "$G/$f"
done
echo "VOICEVOX_HOME=$VV で narrate.py を実行してください(既定値と同じなら不要)"
