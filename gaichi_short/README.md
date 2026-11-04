# 戦前 外地の都市人口ランキング TOP10（ショート動画）

- `gaichi_population_top10.mp4` … 縦型 1080×1920 / 30fps / 約89秒
- ナレーション：VOICEVOX:青山龍星（ノーマル／熱血）
- BGM・効果音：`src/audio.py` でプログラム生成したオリジナル音源
- 数値は1940年頃の概数（記憶ベースの概算。正確な値は昭和15年国勢調査・各総督府統計書で要確認）

## 再生成
1. VOICEVOX ENGINE を `127.0.0.1:50021` で起動
2. `python3 src/tts.py <voice_dir>` → `python3 src/audio.py` → `python3 src/render.py`
   （フォント：Noto Sans JP / Dela Gothic One を `../fonts/package/` に配置）
