#!/usr/bin/env bash
# アップロード用の最終書き出し: 音量を -14 LUFS(YouTube 基準)に正規化し、ステレオ AAC で再多重化する
set -euo pipefail
cd "$(dirname "$0")"
SRC=output/pacific_war_battles_narrated.mp4
OUT=upload
mkdir -p "$OUT"

# 1パス目: 計測
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
# 2パス目: 計測値を使って線形正規化(音質を変えずにゲインだけ調整)
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000,alimiter=limit=0.79:attack=5:release=80:level=false" \
  -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$OUT/pacific_war_battles_final.mp4"

cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
ffmpeg -y -hide_banner -loglevel error -ss 4.0 -i output/pacific_war_battles.mp4 -frames:v 1 -q:v 2 "$OUT/thumbnail.jpg"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT/pacific_war_battles_final.mp4"
ffmpeg -hide_banner -i "$OUT/pacific_war_battles_final.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
