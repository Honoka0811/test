#!/usr/bin/env bash
# アップロード用の最終書き出し: 音量を -14 LUFS(YouTube/TikTok の基準)付近に揃え、ステレオ AAC で再多重化する
set -euo pipefail
cd "$(dirname "$0")"
SRC=output/baito_ranking.mp4
OUT=upload
mkdir -p "$OUT"

# 計測 → 「-14 LUFS に近づける」と「True Peak -1dB を超えない」の小さい方のゲインだけ掛ける
# (loudnorm の dynamic モードに落ちて余計な圧縮がかからないよう、単純な音量調整にする)
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
GAIN=$(echo "$M" | python3 -I -c "import json,sys; m=json.load(sys.stdin); print(round(min(-14-float(m['input_i']), -1-float(m['input_tp'])), 2))")
echo "gain ${GAIN} dB"
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy -af "volume=${GAIN}dB" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$OUT/baito_ranking_final.mp4"

cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
node capture.js --thumb 2.6 >/dev/null
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 "$OUT/thumbnail.jpg"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT/baito_ranking_final.mp4"
ffmpeg -hide_banner -i "$OUT/baito_ranking_final.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
