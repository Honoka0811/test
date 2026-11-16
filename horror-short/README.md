# 深夜2時のインターホン — ホラーショート動画

縦型ショート動画(1080×1920 / 30fps / 52.5秒)。オリジナルの「意味が分かると怖い話」です。

- 完成動画: `output/shinya2ji_interphone.mp4`
- サムネイル: `output/thumbnail.jpg` / 字幕: `output/subtitles_ja.srt`
- タイトル・説明文・タグ案: `output/metadata.md`

| 要素 | 内容 |
|---|---|
| ナレーション | VOICEVOX:四国めたん(ノーマル。終盤は ささやき / ヒソヒソ) |
| BGM・効果音 | `sound.py` で numpy 合成(ドローン、オルゴール、不協和ストリングス、心音、ピンポーン、砂嵐)。外部音源なし |
| 映像 | `render.html` の Canvas 描画を Playwright で 1 フレームずつ撮影 |
| フォント | しっぽり明朝(OFL-1.1、`@fontsource/shippori-mincho`) |

## 視聴維持のための仕掛け

- 冒頭1秒で「見ないでください」という禁止のフック
- 1日目の映像から、女の後ろに部屋と同じ柄のカーテンが薄く映っている(見返し・コメント誘導)
- 最後の「だから、言ったんです。」が冒頭の台詞につながるループ構成

## 再生成

```bash
npm install          # フォント
./build.sh           # narrate.py → sound.py → capture.js → 合成
```

VOICEVOX CORE 0.17.1(Python ホイール、ONNX Runtime、`0.vvm` と `5.vvm`)と `pyopenjtalk` が必要です。
パスは `VOICEVOX_ORT` / `VOICEVOX_VVMS` で指定できます。台本は `script.py` を編集してください(尺は音声の長さから自動で決まります)。

公開時は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画末尾と `metadata.md` の説明文に記載済み)。
