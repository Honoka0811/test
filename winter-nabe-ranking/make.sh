#!/usr/bin/env bash
# 全工程: 台本→音声合成→BGM/効果音ミックス→映像撮影→音量正規化して合成→サムネイル
# 使い方: ./make.sh          (映像の撮影を飛ばす場合: SKIP_VIDEO=1 ./make.sh)
set -euo pipefail
cd "$(dirname "$0")"
OUT=output/winter_nabe_ranking.mp4
mkdir -p output build

python3 script.py
python3 audio.py
[ "${SKIP_VIDEO:-0}" = 1 ] || node capture.js
node capture.js --thumb 5.6
ffmpeg -y -hide_banner -loglevel error -i output/thumbnail.png -q:v 2 output/thumbnail.jpg

# 音量を -14 LUFS / -1.5 dBTP に揃える(ゲイン調整 + リミッタ。2 回測って追い込む)
lufs() { ffmpeg -hide_banner -i "$1" -af ebur128=peak=true -f null - 2>&1 | awk '/^ +I:/{i=$2} /^ +Peak:/{p=$2} END{print i, p}'; }
read I0 _ < <(lufs build/mix.wav)
G=$(python3 -I -c "print(round(-14 - $I0 + 0.3, 2))")
for pass in 1 2; do
  ffmpeg -y -hide_banner -loglevel error -i build/mix.wav \
    -af "volume=${G}dB,alimiter=limit=0.82:attack=3:release=60:level=disabled" -ar 48000 build/master.wav
  read I1 TP < <(lufs build/master.wav)
  G=$(python3 -I -c "print(round($G + (-14 - $I1), 2))")
done
echo "master: ${I1} LUFS, true peak ${TP} dBFS"

ffmpeg -y -hide_banner -loglevel error -i build/video.mp4 -i build/master.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "wrote $OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,channels,sample_rate:format=duration,size -of default=nw=1 "$OUT"
