#!/usr/bin/env bash
# 一括ビルド: ナレーション → 映像 → BGM/効果音ミックス → 合成 → アップロード用書き出し
set -euo pipefail
cd "$(dirname "$0")"
ln -sfn "${VOICEVOX_HOME:-/home/user/vv}/fonts" fonts
python3 narrate.py                      # output/voice.wav, timeline.json, subtitles_ja.srt
node capture.js                         # output/video_silent.mp4, events.json
python3 audio.py                        # output/final_mix.wav(BGM・効果音・ナレーション)
mkdir -p upload
# 音量を YouTube 基準の -14 LUFS に合わせて合成
M=$(ffmpeg -hide_banner -i output/final_mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
gv() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/final_mix.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -preset slow -pix_fmt yuv420p \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(gv input_i):measured_TP=$(gv input_tp):measured_LRA=$(gv input_lra):measured_thresh=$(gv input_thresh):offset=$(gv target_offset):linear=true" \
  -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart upload/midway_short.mp4
cp output/subtitles_ja.srt upload/subtitles_ja.srt
node capture.js --stills 3.6 >/dev/null && ffmpeg -y -loglevel error -i output/stills/t3.60.png -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 upload/midway_short.mp4
ffmpeg -hide_banner -i upload/midway_short.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
