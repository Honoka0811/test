# 空き地の番号 — ホラーショート動画

近所の空き地をテーマにした縦型ホラーショート(1080×1920 / 30fps / 約35秒)。スマホ視点の手ブレ映像で、オチは1つに絞っています。
映像・効果音はすべてコードで生成しており、外部の素材は使っていません。ナレーションは VOICEVOX(青山龍星「しっとり」「囁き」)です。

- **完成動画: `upload/akichi_horror_final.mp4`**(字幕焼き込み・ナレーション・効果音入り、-14 LUFS)
- 字幕: `upload/subtitles_ja.srt` / サムネイル: `upload/thumbnail.jpg` / タイトル・説明文・タグ: `upload/metadata.md`

## ストーリー

| シーン | 内容 |
|---|---|
| 看板(冒頭0秒) | 近所の空き地の看板。電話番号だけ、黒く塗りつぶされてる。 |
| 削る | 気になって、削ってみた。→ 下4桁「4444」 |
| 気づく | スマホのプロフィール画面と見比べる。「これ……俺の番号だ」 |
| 発信 | かけてみた。(呼び出し音) |
| 応答 | 出たのは、俺の声だった。 |
| 電話の声 | 「いま、空き地にいるよ」(電話回線風の声) |
| 探す | 空き地の真ん中で、スマホが光ってた。画面には同じ通話時間 |
| 振り向くな | 通話が切れて暗くなった画面に、肩越しのもう一人が映る。耳元で「振り向いたら、交代な」 |
| エンド | 見ている人のスマホに「着信 090-****-4444」 |

## 再生成の方法

```bash
cd akichi-horror
python3 narrate.py   # ナレーション合成 → output/narration.wav, timeline.js/json(シーン尺), subtitles_ja.srt
python3 sound.py     # 環境音・効果音を合成してナレーションとミックス → output/mix.wav
node capture.js      # render.html を1フレームずつ撮影 → output/video_silent.mp4
./export.sh          # 映像と音声を合成し -14 LUFS に正規化 → upload/
```

- `narrate.py` … 原稿は `SCRIPT` にあります。読み上げの長さからシーンの尺を自動で決めるので、原稿を書き換えても映像・効果音のタイミングが追従します
- `render.html` … Canvas 2D で `render(t)` が時刻 t のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)
- `sound.py` … 爪で削る音、プッシュ音・呼び出し音・終話音、回線ノイズ、足音、バイブ、衝撃音、環境音を numpy だけで合成
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、IPAゴシック、Python 3 + `numpy` + `pyopenjtalk` + `voicevox_core`(セットアップは `../pacific-war-analysis/README.md` と同じ。音声モデルは `15.vvm`)

電話番号は実在の番号にならないよう、中4桁を常に伏せています。
VOICEVOX の音声を公開する場合は「VOICEVOX:青山龍星」のクレジット表記が必要です(エンドカードと説明文に記載済み)。
