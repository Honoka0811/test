#!/usr/bin/env bash
# 一括生成: ナレーション/BGM → 映像 → 合成 → アップロード用書き出し(-14 LUFS)
# 前提: VOICEVOX ENGINE が起動していること
#   docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
node capture.js output/shimoyama_video.mp4
ffmpeg -y -hide_banner -loglevel error -i output/shimoyama_video.mp4 -i output/mix.wav \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart output/shimoyama_narrated.mp4

mkdir -p upload
SRC=output/shimoyama_narrated.mp4
M=$(ffmpeg -hide_banner -i "$SRC" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -c:v libx264 -crf 25 -preset slow -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -movflags +faststart upload/shimoyama_case_final.mp4
cp output/subtitles_ja.srt upload/subtitles_ja.srt
# サムネイル(タイトル画面)
ffmpeg -y -hide_banner -loglevel error -ss 4.5 -i output/shimoyama_video.mp4 -frames:v 1 -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 upload/shimoyama_case_final.mp4
ffmpeg -hide_banner -i upload/shimoyama_case_final.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
