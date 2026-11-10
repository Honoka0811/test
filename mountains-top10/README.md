# 絶対に登るべき山10選 — ショート動画

日本の名山10座を第10位からカウントダウンで紹介する縦型ショート動画(1080×1920 / 30fps / 約79秒)。

- **完成動画: `upload/mountains_top10.mp4`**(-14 LUFS 正規化・ステレオAAC)
- 字幕ファイル: `upload/subtitles_ja.srt`(動画内にも字幕を焼き込み済み)
- ナレーション: VOICEVOX:四国めたん(ノーマル)
- BGM: `bgm.py` で numpy から合成したオリジナル曲(Cメジャー/112BPM。外部音源なし・権利フリー)。ナレーション中は自動で音量を下げる
- 映像: Canvas で各山の特徴を手続き的にイラスト化(写真は不使用)

## ランキング

| 順位 | 山 | 標高 | 地域 | 推しポイント |
|---|---|---|---|---|
| 10 | 高尾山 | 599m | 東京都 | 都心から約1時間、ミシュラン三つ星 |
| 9 | 宮之浦岳 | 1,936m | 鹿児島県・屋久島 | 世界自然遺産の島、九州最高峰 |
| 8 | 旭岳 | 2,291m | 北海道・大雪山 | 北海道最高峰、日本一早い紅葉 |
| 7 | 木曽駒ヶ岳 | 2,956m | 長野県・中央アルプス | ロープウェイで標高2,612mの千畳敷へ |
| 6 | 立山 | 3,015m | 富山県・北アルプス | 日本三霊山、バスで室堂(2,450m)まで |
| 5 | 燕岳 | 2,763m | 長野県・北アルプス | 白い花崗岩の「北アルプスの女王」 |
| 4 | 白馬岳 | 2,932m | 長野県・富山県 | 日本三大雪渓、高山植物 |
| 3 | 北岳 | 3,193m | 山梨県・南アルプス | 日本第2の高峰、固有種キタダケソウ |
| 2 | 槍ヶ岳 | 3,180m | 長野県・岐阜県 | 天を突く穂先 |
| 1 | 富士山 | 3,776m | 静岡県・山梨県 | 日本最高峰、ご来光 |

難易度の★は一般的な登山ルートを想定した目安です。

## 再生成

```bash
./make.sh             # ナレーション付き(VOICEVOX が必要)→ upload/mountains_top10.mp4
./make.sh --no-voice  # ナレーション無し・BGMのみのプレビュー
node capture.js --stills 3 10 20   # 指定秒の静止画を output/stills/ に保存(確認用)
```

- `scenes.json` … 各シーンの文言(`read` = 読み上げ用、`sub` = 字幕用)、山のデータ。ここを書き換えて `./make.sh` で作り直せます
- `narrate.py` … ナレーション合成。各シーンの尺はナレーションの長さに合わせて自動決定(`output/timing.json`)
- `render.html` / `capture.js` … 映像の描画と Playwright による撮影
- `bgm.py` … BGM 合成(`python3 bgm.py 秒数 出力.wav` で単体書き出しも可)

声の調子を変える: `VOICEVOX_STYLE=0 ./make.sh`(0 = あまあま、6 = ツンツン)、話速は `VOICEVOX_SPEED=1.3` など。

### VOICEVOX のセットアップ

`/home/user/vv/` に以下を置いて `voicevox_core` の wheel を pip install(パスは環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVMS` / `VOICEVOX_DICT` で変更可)。

| 必要なもの | 取得元 |
|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` → `ort/` に展開 | VOICEVOX/onnxruntime-builder releases |
| `0.vvm`(四国めたんを含む)→ `vvms/` | VOICEVOX/voicevox_vvm releases (0.16.2) |
| `open_jtalk_dic_utf_8-1.11.tar.gz` → `dict/` に展開 | r9y9/open_jtalk releases |

VOICEVOX の音声を公開する際は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画のエンディングに記載済み。概要欄にも書くのがおすすめ)。
