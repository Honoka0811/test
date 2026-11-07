#!/usr/bin/env bash
# アップロード用の最終書き出し: 音量を -14 LUFS(YouTube 基準)に合わせ、リミッターで音割れを防ぎ、ステレオ AAC で再多重化。字幕・サムネイルも揃える
set -euo pipefail
cd "$(dirname "$0")"
SRC=output/video_narrated.mp4
OUT=upload
mkdir -p "$OUT"
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
# 2パス目: 目標との差分だけゲインを上げ、リミッターでピークを -1.5 dBTP 付近に抑える
GAIN=$(python3 -I -c "print(round(-13.1 - float('$(g input_i)'), 2))")
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v copy \
  -af "aresample=192000,volume=${GAIN}dB,alimiter=limit=0.80:attack=3:release=60:level=false,aresample=48000" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$OUT/japan_zekkei5_shorts.mp4"
cp output/subtitles_ja.srt "$OUT/subtitles_ja.srt"
node capture.js --thumb output/thumbnail.png >/dev/null
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 "$OUT/thumbnail.jpg"
echo "wrote $OUT/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT/japan_zekkei5_shorts.mp4"
ffmpeg -hide_banner -i "$OUT/japan_zekkei5_shorts.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
