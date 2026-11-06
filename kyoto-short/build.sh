#!/usr/bin/env bash
# 一括生成: ナレーション → BGM/効果音ミックス → 映像 → 音声を合成し -14 LUFS に正規化 → upload/ に書き出し
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py
python3 audio.py
node capture.js output/video_only.mp4
node capture.js --stills 5.0 >/dev/null
mkdir -p upload
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_only.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart upload/kyoto_yabai_zatsugaku_top3.mp4
cp output/subtitles_ja.srt upload/subtitles_ja.srt
ffmpeg -y -hide_banner -loglevel error -i output/stills/t5.0.png -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 upload/kyoto_yabai_zatsugaku_top3.mp4
ffmpeg -hide_banner -i upload/kyoto_yabai_zatsugaku_top3.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
