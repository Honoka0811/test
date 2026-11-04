#!/usr/bin/env bash
# 全工程: ナレーション合成 → 映像撮影 → BGM/効果音ミックス → アップロード用書き出し
set -euo pipefail
cd "$(dirname "$0")"
export NODE_PATH=${NODE_PATH:-/opt/node22/lib/node_modules}
mkdir -p output upload
[ "${SKIP_NARRATION:-0}" = 1 ] || python3 narrate.py
[ "${SKIP_VIDEO:-0}" = 1 ] || node capture.js output/video_silent.mp4
python3 audio.py

# サムネイル(タイトルが出た直後のフレーム)
node capture.js --stills 4.6 && ffmpeg -y -loglevel error -i output/stills/t4.60.png -q:v 2 upload/thumbnail.jpg

# -14 LUFS(YouTube 基準)に 2 パスで正規化し、ステレオ AAC で書き出す
SRC=output/video_narrated.mp4
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart upload/nk_missile_30years.mp4
cp output/subtitles_ja.srt upload/subtitles_ja.srt
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 upload/nk_missile_30years.mp4
ffmpeg -hide_banner -i upload/nk_missile_30years.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
