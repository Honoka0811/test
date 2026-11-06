# Octopuses Are Basically ALIENS — 5 Facts That Sound FAKE(英語ショート動画)

海外の視聴者向けの英語ショート動画(1080×1920 / 30fps / 約36.5秒)。
ナレーションは **VOICEVOX:四国めたん**(ノーマル)、BGM と効果音は自作(numpy で合成、権利フリー)。

- **アップロード用一式: `upload/`**
  - `octopus_facts_short.mp4` … 完成動画(-14 LUFS 正規化、ステレオ AAC)
  - `subtitles_en.srt` … 英語字幕
  - `thumbnail.jpg` … サムネイル候補
  - `metadata.md` … タイトル案・説明文・タグ・設定チェックリスト・出典
- 素材: `output/narration.wav`(ナレーションのみ)、`output/bgm.wav`(BGM のみ)、`output/timeline.json`

## 構成(約36秒)

| 時間 | シーン | 内容と演出 |
|---|---|---|
| 0:00 | フック | 「OCTOPUSES ARE ALIENS?!」グリッチ見出し+UFO のビーム、衝撃音。FAKE? → REAL ✓ スタンプ。「WAIT FOR #1!」 |
| 0:06 | #5 | 心臓が3つ。3つの心臓が鼓動(心音 SE と同期)→ メインの心臓が止まって灰色・心電図がフラットに |
| 0:11 | #4 | 血が青い。血のしずくが赤→青に変化、元素カード Cu ✓ / Fe ✗ |
| 0:16 | #3 | 脳が9つ。頭の脳が光り、8本の腕に順番にミニ脳が点灯、カウンターが増える |
| 0:21 | #2 | 腕で味がわかる。巨大な腕が横切り、吸盤が光る → 小さな舌が飛び出す |
| 0:26 | #1 | 一瞬で体色を変える(虹色サイクル)のに色覚が無い → 画面が白黒+グリッチ。直前にスネアロールとライザー → ドロップ |
| 0:32 | アウトロ | 5つのまとめ、コメント誘導。「Because seriously...」で冒頭の画面に戻る無限ループ |

共通演出: 上部の 5→1 トラッカーと進行バー、数字スラム(中央→角のバッジ)、場面転換のホワイトフラッシュ+ウーシュ、
強調語(大文字)での画面シェイクとズーム、キーワードを黄色にした2〜4語ずつのカラオケ風大字幕。

## ナレーションについて(VOICEVOX で英語を話させる工夫)

VOICEVOX は日本語用の音声合成なので、英文をそのまま渡すと「ディイアイディイ…」とアルファベットを1文字ずつ読んでしまいます。
そこで `narrate.py` では各フレーズを **カタカナ英語** で書き(例: `They have THREE hearts!` → `ゼイハヴスリーハーツ!`)、
画面には正しい英語の字幕を表示しています。フレーズ単位のモーラ長から発話タイミングを計算し、字幕と画面演出を声に合わせています。
音声認識(Whisper)で書き起こして、ほぼ原稿どおりの英語として認識されることを確認済みです。

VOICEVOX の利用規約に従い、動画のラストと説明文に「VOICEVOX:四国めたん」のクレジットを入れています。

## 再生成の方法

```bash
cd octopus-facts-short
python3 narrate.py        # ナレーション合成 → output/narration.wav, timeline.js, output/subtitles_en.srt
node capture.js           # render.html を1フレームずつ撮影 → output/octopus_video.mp4(無音)
python3 mix.py            # BGM(ダッキング)+効果音+ナレーションをミックス → upload/octopus_facts_short.mp4
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)
- `bgm.py` … 128BPM・Aマイナー(Am-F-C-G)のポップなビートと効果音を合成
- `fonts/` … Anton / Montserrat(SIL Open Font License)
- 必要なもの: Node.js + `playwright`(Chromium)、ffmpeg、Python 3 + numpy、`voicevox_core` 0.17.1
  (ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3`、音声モデル `0.vvm`、Open JTalk 辞書 `open_jtalk_dic_utf_8-1.11`)。
  パスは環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVMS` / `VOICEVOX_DICT` で指定(既定は `/home/user/vv/` 以下)
- 原稿の差し替えは `narrate.py` の `SCENES`(英語字幕とカタカナ読みのペア)を編集して3コマンドを再実行
