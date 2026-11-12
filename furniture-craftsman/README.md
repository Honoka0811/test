# 家具職人って、どんな仕事? — ショート動画

家具職人の仕事を約57秒で解説する縦型ショート動画(1080×1920 / 30fps)です。
ナレーションは VOICEVOX:四国めたん、BGM は自作(プログラム合成)です。

- 完成動画: `output/furniture_craftsman_short.mp4`
- 字幕: `output/subtitles_ja.srt`(動画にも焼き込み済み)
- サムネイル: `output/thumbnail.png`

## 構成

| シーン | 内容 |
|---|---|
| タイトル | 家具職人って、どんな仕事? |
| 仕事 | 椅子・テーブル・たんすなどを木材から作る/設計から仕上げまで |
| 工程 | 木取り → 加工(かんな・ノミ) → 組立・仕上げ |
| 技 | ほぞ組み(ほぞ・ほぞ穴)のアニメーション |
| 木の性質 | 湿気で伸び縮みする木の動きを読む |
| なるには | 訓練校・工房での修業/家具製作技能士(国家資格) |
| まとめ | 3つのポイント + クレジット |

## 再生成の方法

```bash
python3 narrate.py   # ナレーション合成 → output/narration.wav, timing.js, subtitles_ja.srt
node capture.js      # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py       # BGM生成 + ダッキングしてミックス(-14 LUFS) → output/furniture_craftsman_short.mp4
```

- `narrate.py` … 原稿(`SCENES`)を文ごとに合成し、60秒未満に収まるよう話速を自動調整。各文の開始・終了時刻を `timing.js` に書き出す
- `render.html` … Canvas 2D で `render(t)` が時刻 t のフレームを描画。映像と字幕は `timing.js` に同期(ブラウザで開くとプレビュー、`?t=10` で静止画)
- `bgm.py` … Cメジャー / 100BPM のほのぼの系BGM(マリンバ風メロディ・アルペジオ・ベース・ウッドブロック)を numpy だけで合成
- `mix.py` … ナレーション中は BGM を自動で下げてミックス

必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `pyopenjtalk`(辞書用)、VOICEVOX CORE。
VOICEVOX は `voicevox_core` 0.17.1 の wheel、`voicevox_onnxruntime` 1.17.3、音声モデル `0.vvm`(四国めたん)を GitHub リリースから取得し、
`VOICEVOX_ORT`(`libvoicevox_onnxruntime.so` のパス)と `VOICEVOX_VVMS`(`0.vvm` を置いたディレクトリ)で場所を指定します。

## クレジット・ライセンス

- 音声: **VOICEVOX:四国めたん**(公開時はこのクレジット表記が必要です。動画の最後に記載済み)
- フォント: M PLUS Rounded 1c(SIL Open Font License 1.1)
- BGM・イラスト: このリポジトリのコードで生成したオリジナル
