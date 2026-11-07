#!/usr/bin/env bash
# 必要な外部ファイル(VOICEVOX CORE・ONNX Runtime・音声モデル・辞書・フォント)を vendor/ に取得する
set -euo pipefail
cd "$(dirname "$0")"
V=vendor; mkdir -p $V/dl $V/ort $V/vvms $V/dict $V/fonts
GH=https://github.com
get() { [ -s "$2" ] || curl -fsSL --retry 3 -o "$2" "$1"; }
get $GH/VOICEVOX/voicevox_core/releases/download/0.17.1/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl $V/dl/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
get $GH/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz $V/dl/ort.tgz
get $GH/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz $V/dl/dict.tar.gz
get $GH/VOICEVOX/voicevox_vvm/releases/download/0.17.1/0.vvm $V/vvms/0.vvm   # 0.vvm = 四国めたん・ずんだもん ほか
get https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansCJKjp-Black.otf $V/fonts/NotoSansJP-Black.otf
get https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf $V/fonts/NotoSansJP-Bold.otf
get https://raw.githubusercontent.com/google/fonts/main/ofl/delagothicone/DelaGothicOne-Regular.ttf $V/fonts/DelaGothicOne-Regular.ttf
tar xzf $V/dl/ort.tgz -C $V/ort
tar xzf $V/dl/dict.tar.gz -C $V/dict
pip install -q $V/dl/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl numpy scipy
echo "setup done"
