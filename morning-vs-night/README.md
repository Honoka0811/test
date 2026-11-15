# 朝型 VS 夜型 対決! — ショート動画

朝型(太陽キャラ)と夜型(月キャラ)が4ラウンドで対決する縦型ショート動画(1080×1920 / 30fps / 約59秒)。
ナレーションは VOICEVOX:四国めたん(ノーマル)、BGM・効果音は numpy で合成したオリジナル(権利フリー)。

- 完成動画: `output/morning_vs_night.mp4`(-14 LUFS 目安に正規化済み)
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.png`

## 構成

| シーン | 内容 |
|---|---|
| タイトル | 朝型 VS 夜型 どっちが強い!? |
| 選手入場 | 赤コーナー 朝型(起床5:00)/ 青コーナー 夜型(就寝2:00) |
| ROUND 1 集中力 | 朝型の勝ち |
| ROUND 2 ひらめき | 夜型の勝ち |
| ROUND 3 社会との相性 | 朝型の勝ち |
| FINAL ROUND ひとりの時間 | 夜型の勝ち |
| 結果発表 | 2対2の引き分け。朝型・夜型は遺伝の影響も大きい → 自分のリズムが一番 |
| エンディング | あなたはどっち派? コメントで教えてね |

## 再生成

```bash
./build.sh
```

- `script.py` … 台本(読み上げ用テキストと字幕テキスト)。「朝型」は誤読(チョーガタ)を防ぐため読み上げ側を「あさがた」表記
- `narrate.py` … VOICEVOX で合成 → 実際の音声長からシーン尺を決めて `output/timeline.js` を出力、BGM をダッキングしつつ効果音とミックス
- `bgm.py` … 124BPM のポップなBGM(キック/クラップ/ハイハット/ベース/裏打ちコード/ベル)と効果音
- `render.html` … Canvas 2D で `render(t)` を描画(ブラウザで開くとプレビュー再生)
- `capture.js` / `snapshot.js` … Playwright で全フレーム撮影して mp4 化 / 確認用の静止画書き出し

VOICEVOX CORE 0.16.4・`voicevox_onnxruntime` 1.17.3・`0.vvm`(四国めたんを含む)が必要です。パスは環境変数
`VOICEVOX_ORT` / `VOICEVOX_VVMS` で指定(既定は `/home/user/vv/...`)。話者は `VOICEVOX_STYLE`(既定 2 = 四国めたん ノーマル)。
公開時は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画のエンディングにも記載済み)。
