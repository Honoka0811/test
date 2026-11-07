#!/usr/bin/env bash
# 一括ビルド: ナレーション → BGM/効果音ミックス → 映像撮影 → 音声合成・-14 LUFS 正規化 → upload/ へ書き出し
# 使い方: ./build.sh            (全工程)
#         ./build.sh --no-video (映像の再撮影を省略し、既存の output/video_silent.mp4 を使う)
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
python3 mix.py
[[ "${1:-}" == "--no-video" ]] || node capture.js output/video_silent.mp4
node snap.js --thumb output/thumbnail.png

OUT=upload; mkdir -p "$OUT"
FINAL="$OUT/daily_habits_short.mp4"
# 1パス目で計測 → 2パス目で線形にゲインだけ調整(YouTube の基準 -14 LUFS / True Peak -1.5 dB)
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ar 48000 -ac 2 -c:a aac -b:a 192k -shortest -movflags +faststart "$FINAL"
cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 "$OUT/thumbnail.jpg"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$FINAL"
ffmpeg -hide_banner -nostats -i "$FINAL" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
