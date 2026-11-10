#!/usr/bin/env bash
# 一括生成: ナレーション合成 → 映像レンダリング → 音声合成 → アップロード用書き出し
#   ./make.sh            VOICEVOX(四国めたん)のナレーション付き
#   ./make.sh --no-voice ナレーション無し(BGMのみ)のプレビュー
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output upload
if [ "${1:-}" = "--no-voice" ]; then rm -f output/timing.json; NAME=mountains_top10_preview_bgm_only; else NAME=mountains_top10; fi
python3 narrate.py "$@"
node capture.js output/mountains_top10_silent.mp4
# -14 LUFS(YouTube基準)に正規化してステレオAACで多重化
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/mountains_top10_silent.mp4 -i output/mix.wav -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "upload/$NAME.mp4"
[ -f output/subtitles_ja.srt ] && [ "$NAME" = mountains_top10 ] && cp output/subtitles_ja.srt upload/
echo "wrote upload/$NAME.mp4"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 "upload/$NAME.mp4"
