# 職人系の仕事10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約65秒)。ナレーションは VOICEVOX:四国めたん、BGM は自作(numpy 合成・権利フリー)。

- 完成動画: `output/shokunin_10sen.mp4`
- 字幕: `output/subtitles_ja.srt` / ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`

紹介する仕事: 大工・左官・とび職・溶接工・電気工事士・配管工・塗装工・板金工・庭師・畳職人

## 再生成

```bash
python3 narrate.py   # 音声合成 + BGM + ミックス、timeline.js(シーンの時刻)を書き出す
node capture.js      # render.html を1フレームずつ撮影し、音声と合わせて mp4 化
```

- 原稿・表示テキストは `content.json`。`say` が読み上げ、`tag` などが画面表示。`kana:` で始まる `say` は読みを直接指定
- 映像は `render.html`(Canvas 2D)。シーンの長さはナレーションの長さから自動で決まる
- 必要なもの: Python 3 + numpy + voicevox_core 0.17.1(ONNX Runtime・`0.vvm`・Open JTalk 辞書。パスは `narrate.py` 冒頭の環境変数)、Node.js + playwright、ffmpeg、Noto Color Emoji
- フォント: M PLUS Rounded 1c / Dela Gothic One(SIL OFL、`fonts/` にライセンス同梱)

公開時は VOICEVOX の利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画の最後に表示済み)。
