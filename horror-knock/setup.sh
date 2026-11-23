#!/usr/bin/env bash
# 必要なもの一式を取得する(VOICEVOX CORE・ONNX Runtime・四国めたんの音声モデル・明朝体フォント)
# 置き場所は VV_HOME(既定 /home/user/vv)。フォントは ./fonts にコピーする。
set -euo pipefail
cd "$(dirname "$0")"
VV="${VV_HOME:-/home/user/vv}"
mkdir -p "$VV/ort" "$VV/vvms" "$VV/fonts" fonts

pip install -q numpy scipy pyopenjtalk
if ! python3 -c "import voicevox_core" 2>/dev/null; then
  curl -sSLf -o "$VV/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl" \
    https://github.com/VOICEVOX/voicevox_core/releases/download/0.17.1/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
  pip install -q "$VV/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl"
fi
if [ ! -d "$VV/ort/voicevox_onnxruntime-linux-x64-1.17.3" ]; then
  curl -sSLf https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C "$VV/ort"
fi
# 0.vvm = 四国めたん ノーマル/あまあま/ツンツン/セクシー、5.vvm = 四国めたん ささやき/ヒソヒソ
for m in 0 5; do
  [ -f "$VV/vvms/$m.vvm" ] || curl -sSLf -o "$VV/vvms/$m.vvm" https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.17.0/$m.vvm
done
python3 -c "import pyopenjtalk; pyopenjtalk.g2p('辞書')" >/dev/null   # Open JTalk 辞書の取得

# Noto Serif JP(SIL Open Font License)
if [ ! -f fonts/NotoSerifJP-Black.otf ]; then
  curl -sSLf -o "$VV/fonts/NotoSerifJP.zip" https://github.com/notofonts/noto-cjk/releases/download/Serif2.003/12_NotoSerifJP.zip
  python3 - "$VV/fonts/NotoSerifJP.zip" <<'EOF'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
for n in ('Medium', 'Bold', 'Black'):
    open(f'fonts/NotoSerifJP-{n}.otf', 'wb').write(z.read(f'SubsetOTF/JP/NotoSerifJP-{n}.otf'))
open('fonts/LICENSE', 'wb').write(z.read('LICENSE'))
EOF
fi
echo "setup done"
