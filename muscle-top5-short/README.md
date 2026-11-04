# 鍛えると得する筋肉 TOP5（ショート動画）

`muscle_top5_short.mp4` — 1080×1920 / 30fps / 約71秒

- ナレーション：VOICEVOX:青山龍星（ノーマル＋熱血）
- BGM・効果音：`src/audio.py` で一から合成したオリジナル（124BPM EDM）
- 映像：`src/scene.html`（Canvas）を Chromium でフレーム描画

## 再生成
VOICEVOX エンジンを `127.0.0.1:50021` で起動した状態で：
```
python3 src/tts.py     # ナレーション生成＋拍に合わせたタイムライン
python3 src/audio.py   # BGM/SE 合成とミックス
node src/render.js     # 映像描画＋エンコード
```
