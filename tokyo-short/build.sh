#!/usr/bin/env bash
# 一括ビルド: ナレーション → BGM/効果音ミックス → 映像 → アップロード用一式(upload/)
set -euo pipefail
cd "$(dirname "$0")"
export NODE_PATH=${NODE_PATH:-$(npm root -g)}
python3 tts.py
python3 audio.py
node capture.js
mkdir -p upload
# -14 LUFS(YouTube 基準)へ 2 パスで正規化してステレオ AAC で多重化
M=$(ffmpeg -hide_banner -i output/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -hide_banner -loglevel error -i output/video.mp4 -i output/mix.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" \
  -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart upload/tokyo_secrets_short.mp4
# 字幕 SRT
python3 - <<'PY'
import json
tl = json.load(open('output/timeline.json'))
ts = lambda t: f"{int(t//3600):02d}:{int(t%3600//60):02d}:{int(t%60):02d},{int(round(t%1*1000))%1000:03d}"
cues = [l for s in tl['scenes'] for l in s['lines']]
with open('upload/subtitles_ja.srt', 'w', encoding='utf-8') as f:
    for i, l in enumerate(cues, 1):
        end = cues[i]['start'] if i < len(cues) else tl['total']
        f.write(f"{i}\n{ts(l['start'])} --> {ts(end)}\n{l['text'].replace('【','').replace('】','').replace(chr(10),' ')}\n\n")
PY
# サムネイル(冒頭フック)
node capture.js --stills 2.2 && ffmpeg -y -hide_banner -loglevel error -i output/stills/t2.20.png -q:v 2 upload/thumbnail.jpg
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels:format=duration,size -of default=nw=1 upload/tokyo_secrets_short.mp4
ffmpeg -hide_banner -i upload/tokyo_secrets_short.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
