# 九州大学のここがすごい！10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約58秒)。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGM は自作のポップ曲(numpy で合成、権利フリー)。

- **完成動画: `output/kyushu_univ_top10.mp4`**(音量 -14 LUFS に正規化済み)
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg`

## 構成(10位→1位のカウントダウン)

| 順位 | 項目 | 画面のポイント |
|---|---|---|
| 導入 | 九州大学のここがすごい！10選 | |
| 10 | 12学部の総合大学 | 学生数 約1万8千人 |
| 9 | 芸術工学部 | 工学 × デザイン |
| 8 | 卒業生・中村哲医師 | アフガニスタンで用水路 |
| 7 | 風レンズ風車 | 九大生まれの技術 |
| 6 | 九州大学病院 | 九州最大級の大学病院 |
| 5 | 椎木講堂 | 設計:伊東豊雄 |
| 4 | I²CNER | WPI 世界トップレベル研究拠点 |
| 3 | 水素エネルギー研究 | キャンパス内に水素ステーション |
| 2 | 指定国立大学法人 | 2021年指定 |
| 1 | 伊都キャンパスの広さ | 約272ha・東京ドーム約58個分 |
| 締め | いくつ知ってた？フォローしてね | クレジット |

数値は概数です。公開前に最新の公式情報(九州大学ウェブサイト等)で確認してください。

## 再生成の方法

```bash
python3 voice.py   # ナレーション合成 → output/narration.wav, timeline.js(各シーンの尺), 字幕SRT
node capture.js    # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py     # BGM をダッキングしてミックス、-14 LUFS 正規化 → output/kyushu_univ_top10.mp4
```

- `script.py` … 台本。`read` は読み上げ用(固有名詞はかな表記で読みを固定)、`sub` は字幕表示用。書き換えて上の3コマンドを実行すれば尺も自動で追従します
- `voice.py` … VOICEVOX CORE 0.17.1 で合成(話者スタイル `VOICEVOX_STYLE`、既定 2 = 四国めたん ノーマル。話速 `VOICE_SPEED` 既定 1.28)
- `render.html` … Canvas 2D の `render(t)` で各フレームを描画(ブラウザで開くとプレビュー再生)。イラストはすべてコードで描画
- `bgm.py` … C メジャー/128BPM、王道進行のポップ BGM。`python3 bgm.py 60 bgm.wav` で単体書き出し
- `mix.py` … ナレーション中は BGM を約 -8dB 下げる(声が BGM より約 10dB 大きい)
- VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ手順で、音声モデルは `0.vvm`(四国めたん収録)を使用。Open JTalk 辞書は `open_jtalk_dic_utf_8-1.11`(r9y9/open_jtalk releases)を `VOICEVOX_DICT` で指定

## クレジット・ライセンス

- ナレーション:**VOICEVOX:四国めたん**(公開時は動画内・概要欄にこの表記が必要。動画末尾に記載済み)
- BGM:オリジナル(本リポジトリの `bgm.py` で生成)
- フォント:M PLUS Rounded 1c(SIL Open Font License 1.1、`fonts/OFL.txt`)
