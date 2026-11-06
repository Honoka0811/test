#!/usr/bin/env bash
# 必要な外部ファイル(VOICEVOX CORE・四国めたんの音声モデル・辞書・フォント)を ~/vv に取得する
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
VV=${VOICEVOX_HOME:-/home/user/vv}
mkdir -p "$VV/vvms" "$VV/ort" "$VV/fonts/noto" "$VV/fonts/dela"
cd "$VV"
GH=https://github.com/VOICEVOX
[ -f voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl ] || curl -sSLO $GH/voicevox_core/releases/download/0.17.1/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
[ -d ort/voicevox_onnxruntime-linux-x64-1.17.3 ] || { curl -sSL $GH/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C ort; }
[ -f vvms/0.vvm ] || curl -sSL -o vvms/0.vvm $GH/voicevox_vvm/releases/download/0.16.2/0.vvm   # 0.vvm = 四国めたん
[ -d open_jtalk_dic_utf_8-1.11 ] || { curl -sSL https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz | tar xz; }
[ -d fonts/noto/package ] || { curl -sSL https://registry.npmjs.org/@fontsource/noto-sans-jp/-/noto-sans-jp-5.0.19.tgz | tar xz -C fonts/noto; }
[ -d fonts/dela/package ] || { curl -sSL https://registry.npmjs.org/@fontsource/dela-gothic-one/-/dela-gothic-one-5.0.12.tgz | tar xz -C fonts/dela; }
pip install -q "$VV"/voicevox_core-0.17.1-*.whl numpy scipy
ln -sfn "$VV/fonts" "$HERE/fonts"
echo "setup done: $VV"
