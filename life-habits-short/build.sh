#!/usr/bin/env bash
# 一括ビルド: ナレーション → BGM/効果音ミックス → 映像 → 音量正規化して最終 mp4
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py          # output/narration.wav, timeline.js, output/timeline.json, output/subtitles_ja.srt
python3 music.py            # output/bgm.wav, sfx.wav, mix.wav
node capture.js output/video_silent.mp4   # 映像 + output/thumbnail.png

# 音量を -14 LUFS(YouTube/TikTok の基準)に 2 パスで正規化し、ステレオ AAC で多重化
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
mkdir -p upload
ffmpeg -y -hide_banner -loglevel error -i output/video_silent.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart upload/life_habits_10.mp4
cp output/subtitles_ja.srt upload/subtitles_ja.srt
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 upload/life_habits_10.mp4
ffmpeg -hide_banner -i upload/life_habits_10.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
