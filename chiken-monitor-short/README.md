# 治験モニターのお仕事 — ショート動画

治験モニター(治験ボランティア)とは何かを約60秒で紹介する縦型ショート動画(1080×1920 / 30fps / 59.8秒)。

- 完成動画: `output/chiken_monitor_short.mp4`(ナレーション+BGM、-14 LUFS)
- 字幕: `output/subtitles_ja.srt` / ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`
- ナレーション: **VOICEVOX:四国めたん**(ノーマル)。公開時はこのクレジット表記が必要(動画内に記載済み)
- BGM: `bgm.py` で合成した自作曲(外部音源なし・権利表記不要)

## 構成

つかみ → 治験とは → アルバイトではなくボランティア(負担軽減費) → 参加の流れ → 負担軽減費の目安 → 注意点 → 安全のしくみ → まとめ

金額(通院1回 約7千〜1万円)や参加間隔(3〜4か月)は一般的な目安で、試験ごとに異なります。

## 再生成

```bash
npm install                 # フォント(M PLUS Rounded 1c)
python3 build_audio.py      # ナレーション合成 → timeline.js / SRT / BGM / output/mix.wav
node capture.js             # render.html を撮影して mp4 化
```

- 原稿は `build_audio.py` の `SCRIPT`。音声の長さから `timeline.js` が作られ、画面(`render.html`)はそれに同期します
- 必要なもの: Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + pyopenjtalk + voicevox_core 0.17.1、
  VOICEVOX ONNX Runtime(`VOICEVOX_ORT`)、音声モデル `0.vvm`(`VOICEVOX_VVMS`)
