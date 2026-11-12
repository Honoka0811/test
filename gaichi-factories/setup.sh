#!/usr/bin/env bash
# 再生成に必要な外部ファイルを取得する(VOICEVOX CORE 一式・フォント・Natural Earth)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p vendor/voicevox vendor/ne fonts
dl() { [ -s "$1" ] || curl -fsSL --retry 3 -o "$1" "$2"; }
V=vendor/voicevox
dl $V/voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.0/voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl
dl $V/ort.tgz https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz
dl $V/dic.tar.gz https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz
dl $V/0.vvm https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.16.0/0.vvm
tar xzf $V/ort.tgz -C $V && tar xzf $V/dic.tar.gz -C $V
pip install -q $V/voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl numpy geopandas
dl fonts/NotoSansJP.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
dl vendor/ne/c.zip https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip
dl vendor/ne/p.zip https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip
unzip -qo vendor/ne/c.zip -d vendor/ne/c && unzip -qo vendor/ne/p.zip -d vendor/ne/p
echo "ok"
