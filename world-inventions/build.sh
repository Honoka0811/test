#!/usr/bin/env bash
# 一括生成: ナレーション+BGM → 映像 → 合成 → アップロード用書き出し(-14 LUFS)
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py                       # output/narration.wav, bgm.wav, mix.wav, subtitles_ja.srt, timeline.js
node capture.js output/video_silent.mp4  # render.html を 30fps で撮影
mkdir -p upload
SRC=output/video_silent.mp4; MIX=output/mix.wav; OUT=upload/world_inventions_top10.mp4
# 1パス目で計測 → 2パス目で線形ゲイン調整(-14 LUFS / TP -1.5)
M=$(ffmpeg -hide_banner -i "$MIX" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -i "$MIX" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
cp output/subtitles_ja.srt upload/subtitles_ja.srt
# サムネイル(タイトル画面)
ffmpeg -y -hide_banner -loglevel error -ss 2.0 -i "$SRC" -frames:v 1 -q:v 2 upload/thumbnail.jpg
echo "wrote upload/"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT"
ffmpeg -hide_banner -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
