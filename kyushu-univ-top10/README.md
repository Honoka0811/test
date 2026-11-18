# 九州大学のここがすごい！10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約65秒)。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGM は自作のポップ曲(numpy で合成、権利フリー)。

- **完成動画: `output/kyushu_univ_top10.mp4`**(音量 -14 LUFS に正規化済み)
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg`

## 構成(10位→1位のカウントダウン・約65秒)

| 順位 | 項目 | 根拠・補足 |
|---|---|---|
| 導入 | 九大生でも知らない！？ここがすごい10選 | |
| 10 | 大学に水素ステーション | 伊都キャンパス内の水素ステーション |
| 9 | 風レンズ風車 | 九大応用力学研究所発の集風型風車 |
| 8 | 九州大学なのに北海道に森 | 農学部附属 北海道演習林(全域が鳥獣保護区) |
| 7 | キャンパスにイノシシ | 大学の案内マップに「イノシシ出没エリア」表示、2015年に駆除告知 |
| 6 | 卒業生・中村哲医師 | 九大医学部卒、アフガニスタンで用水路建設 |
| 5 | 第3世代の有機EL(TADF) | 安達千波矢教授、2012年発表、レアメタル不要。Kyulux が実用化 |
| 4 | カイコの保存数 世界最大 | NBRP カイコ中核機関。コア系統 495(2015年度報告) |
| 3 | 1968年 米軍機墜落 | 箱崎キャンパスの建設中の大型計算機センターに RF-4C が墜落、けが人なし |
| 2 | 広すぎるキャンパス | 約272ha、東西約3km・南北約2.5km |
| 1 | 1400年以上前の刀が出土 | 元岡古墳群G-6号墳の庚寅銘大刀(570年、金象嵌19字)、2019年 国の重要文化財 |

数値は概数です。公開前に最新の公式情報で確認してください。

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
- `mix.py` … ナレーション中は BGM を約 -8dB 下げる(声が BGM より約 10dB 大きい)。順位が出るたびに効果音(シュッ+ドン)を合成
- VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ手順で、音声モデルは `0.vvm`(四国めたん収録)を使用。Open JTalk 辞書は `open_jtalk_dic_utf_8-1.11`(r9y9/open_jtalk releases)を `VOICEVOX_DICT` で指定

## クレジット・ライセンス

- ナレーション:**VOICEVOX:四国めたん**(公開時は動画内・概要欄にこの表記が必要。動画末尾に記載済み)
- BGM:オリジナル(本リポジトリの `bgm.py` で生成)
- フォント:M PLUS Rounded 1c(SIL Open Font License 1.1、`fonts/OFL.txt`)
