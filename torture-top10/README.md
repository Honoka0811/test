# 歴史上最悪の拷問10選 — ショート動画

縦型ショート(1080×1920 / 30fps)。ナレーションは VOICEVOX:四国めたん(style 2)、BGM は `bgm.py` で自作合成(権利フリー)。

- 完成動画: `output/worst_torture_top10.mp4`(-14 LUFS / ステレオAAC)
- 字幕: `output/subtitles_ja.srt` / ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`

## 生成

```bash
./build.sh   # narrate.py → capture.js → mix.py
```

- `script.json` … 原稿(読み上げ用 `say` と字幕用 `sub`)。ここを書き換えて再実行すれば差し替え可能
- `narrate.py` … 音声合成。セリフの長さから各シーンの尺を自動で決め `output/timeline.json(.js)` を出力。voicevox_core が無い環境では Open JTalk にフォールバック
- `render.html` … Canvas で時刻 t のフレームを描画(ブラウザで開くとプレビュー)
- `capture.js` … Playwright で全フレームを撮影して mp4 化
- `bgm.py` … Cマイナーのダーク系BGM(ドローン+弦パッド+オルゴール+心音)。各順位の切り替わりに衝撃音
- `mix.py` … ナレーション中は BGM を自動で下げてミックスし、最終 mp4 を出力

VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ(音声モデルは `0.vvm` = 四国めたん)。
公開時は「VOICEVOX:四国めたん」のクレジット表記が必要です(画面左下に自動表示)。
