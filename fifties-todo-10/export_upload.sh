#!/usr/bin/env bash
# 最終書き出し: 無音の動画(capture.js)にミックス音声(narrate.py)を合成し、
# 音量を -14 LUFS(YouTube 基準)に正規化してアップロード用一式を upload/ に揃える
set -euo pipefail
cd "$(dirname "$0")"
VIDEO=output/fifties_todo_10.mp4
MIX=output/mix.wav
NARRATED=output/fifties_todo_10_narrated.mp4
OUT=upload
mkdir -p "$OUT"

# 1) 映像 + ミックス音声
ffmpeg -y -hide_banner -loglevel error -i "$VIDEO" -i "$MIX" -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$NARRATED"

# 2) ラウドネス計測 → 線形正規化(音質を変えずにゲインだけ調整)
M=$(ffmpeg -hide_banner -i "$NARRATED" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$NARRATED" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$OUT/fifties_todo_10_final.mp4"

# 3) 字幕・サムネイル
cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
node capture.js --frames 2.6 output/frames >/dev/null
ffmpeg -y -hide_banner -loglevel error -i output/frames/t2_60.png -q:v 2 "$OUT/thumbnail.jpg"
cp output/frames/t2_60.png output/thumbnail.png

echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT/fifties_todo_10_final.mp4"
ffmpeg -hide_banner -i "$OUT/fifties_todo_10_final.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
