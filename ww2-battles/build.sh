#!/usr/bin/env bash
# 一括ビルド: ナレーション+BGM → 映像 → 合成 → アップロード用書き出し(-14 LUFS)
set -euo pipefail
cd "$(dirname "$0")"
python3 narrate.py                       # output/narration.wav, bgm.wav, mix.wav, cues.js, subtitles_ja.srt
node capture.js output/ww2_battles_video.mp4   # 字幕焼き込み済みの映像(無音)
mkdir -p upload
OUT=upload/ww2_major_battles.mp4
# 1パス目で計測 → 2パス目で線形ゲイン調整(-14 LUFS / TP -1.5)
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/ww2_battles_video.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ac 2 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
cp output/subtitles_ja.srt upload/subtitles_ja.srt
ffmpeg -y -hide_banner -loglevel error -ss 10.5 -i output/ww2_battles_video.mp4 -frames:v 1 -q:v 2 upload/thumbnail.jpg
echo "wrote $OUT (narration engine: $(cat output/engine.txt))"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT"
ffmpeg -hide_banner -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tr -s ' '
