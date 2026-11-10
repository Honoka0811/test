# 死ぬ前に絶対やったほうがいいこと10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約71秒)。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGM はプログラムで合成したオリジナル曲(権利フリー)。

- **完成動画: `output/bucket_list_10.mp4`**(-15 LUFS 前後、ステレオ AAC)
- 字幕ファイル: `output/subtitles_ja.srt`(字幕は動画にも焼き込み済み)

## 構成(カウントダウン形式)

| 順位 | 項目 |
|---|---|
| タイトル | 死ぬ前に絶対やったほうがいいこと10選 |
| 10 | 熱気球に乗る |
| 9 | フルマラソンを完走する |
| 8 | 満天の星空の下でキャンプ |
| 7 | スキューバダイビング |
| 6 | 富士山頂でご来光を見る |
| 5 | 世界一周旅行 |
| 4 | オーロラを見る |
| 3 | スカイダイビング |
| 2 | 親を旅行に連れて行く |
| 1 | 大切な人に「ありがとう」を伝える |
| エンディング | 10項目のチェックリスト +「コメントで教えてね!」 |

イラストはすべて Canvas でコード描画(外部画像なし)。

## ファイル

| ファイル | 役割 |
|---|---|
| `script.py` | 原稿(読み上げ用テキストと字幕用テキスト)。ここを書き換えれば内容を差し替えられる |
| `narrate.py` | 音声合成 → シーン尺を決めて `timeline.js` を生成。`mux` で BGM・効果音をミックスして完成 mp4 を作る |
| `bgm.py` | BGM 合成(Cメジャー / 118BPM / 王道進行) |
| `render.html` | 映像。`render(t)` が時刻 t のフレームを描く |
| `capture.js` | render.html を Playwright で 1 フレームずつ撮影して mp4 化 |
| `fonts/` | Dela Gothic One、M PLUS Rounded 1c(いずれも SIL OFL) |

## 再生成

```bash
python3 narrate.py        # ナレーション合成 + timeline.js / 字幕 SRT
node capture.js           # output/video.mp4(無音)
python3 narrate.py mux    # BGM・効果音をミックスして output/bucket_list_10.mp4
```

VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ(音声モデルは四国めたんを含む `0.vvm`)。
話者は `VOICEVOX_STYLE` で変更可能(2=四国めたん ノーマル、0=あまあま、6=ツンツン、3=ずんだもん)。

公開時は利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(エンディング画面に記載済み。概要欄にも書くのがおすすめ)。
