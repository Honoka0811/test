# 快適ネット回線 TOP5（ショート動画）

- 完成動画: `provider_ranking_short.mp4`（1080x1920 / 30fps / 約54秒）
- ナレーション: VOICEVOX:四国めたん（投稿時は概要欄などにクレジット「VOICEVOX:四国めたん」を記載）
- BGM・効果音: `audio.py` で数値合成したオリジナル（権利フリー）
- フォント: Dela Gothic One / M PLUS Rounded 1c（SIL OFL）

## 再生成手順
1. `python3 narration.py <VOICEVOX素材dir>` … 音声と build/timeline.json を生成
2. `python3 audio.py` → `ffmpeg -i build/mix.wav -af loudnorm=I=-14:TP=-1 build/mix_norm.wav && mv build/mix_norm.wav build/mix.wav`
3. `fonts/` にフォントを置き、`node render.js`（プレビューは `node render.js 5,13,39`）
