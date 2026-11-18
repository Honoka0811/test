#!/usr/bin/env bash
# 一括生成: ナレーション+BGM → 映像 → 音量を -14 LUFS に正規化して合成
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules ] || npm install --no-audit --no-fund
python3 narrate.py
node capture.js output/video_silent.mp4   # 中間ファイル(高画質)。最終エンコードは下の ffmpeg
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -c:v libx264 -crf 21 -preset slow -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,volume=1.3dB" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart output/beppan_short.mp4
node thumbnail.js   # output/thumbnail_tall.jpg(縦)・thumbnail_wide.jpg(横)
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 output/beppan_short.mp4
ffmpeg -hide_banner -i output/beppan_short.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
