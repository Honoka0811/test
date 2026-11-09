# 会社で働きやすくなるために、資格は重要？ — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約67秒)。ナレーションは **VOICEVOX:四国めたん(ノーマル)**、BGM は自作(numpy で合成、権利フリー)。

- **完成動画: `output/shikaku_short.mp4`**(字幕焼き込み・ナレーション+BGM、-15 LUFS 前後)
- 字幕ファイル: `output/subtitles_ja.srt`
- サムネイル: `output/thumbnail.png`

## 構成

| シーン | 内容 |
|---|---|
| タイトル | 会社で働きやすくなる？ 資格取得は重要なのか |
| 結論 | 目的があれば資格は強い武器。ただし取るだけでは働きやすくならない |
| メリット① | スキルを客観的に示せる → 説明しやすい・任されやすい |
| メリット② | 資格手当・昇格要件になる会社も(就業規則・人事制度を確認) |
| メリット③ | 知識が体系的に身につく → 自信がつき仕事が楽に |
| 注意点 | 資格だけでは評価されない／無関係な資格は時間とお金の負担 |
| 3つチェック | 今の仕事で使う？ 会社が評価する？ 将来のキャリアにつながる？ |
| まとめ | 資格 × 実務 = 働きやすさ。資格はゴールではなく道具 |

## 再生成

```bash
./build.sh   # narrate.py → capture.js → mix.py
```

- `script.js` … ナレーション原稿(読み上げ用 `read` と字幕用 `sub`)。書き換えて `./build.sh` で作り直せる
- `narrate.py` … VOICEVOX で文ごとに合成し、音声の長さからシーン尺を決めて `timing.js`・`output/narration.wav`・SRT を出力
- `render.html` … Canvas で `render(t)` を描画(ブラウザで開くとプレビュー再生)。`timing.js` に合わせて字幕を切り替え
- `capture.js` … Playwright で全フレームを撮影し ffmpeg で `output/video_silent.mp4` に
- `bgm.py` … 明るいオフィス系ポップ(F メジャー / 108BPM。エレピ+マリンバ+ベース+軽いドラム)
- `mix.py` … ナレーション中は BGM を自動で下げて(ダッキング)ミックスし、-14 LUFS 目標で正規化して最終 mp4 を出力
- `snap.js` … 指定時刻のフレームを PNG に書き出す確認用(`node snap.js 出力dir 2.2 10 ...`)

### VOICEVOX のセットアップ

`/home/user/vv`(`VOICEVOX_HOME` で変更可)に以下を置く:

| 物 | 取得元 |
|---|---|
| `voicevox_core-0.16.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` |
| `ort/voicevox_onnxruntime-linux-x64-1.17.3/` | VOICEVOX/onnxruntime-builder releases |
| `vvms/0.vvm`(四国めたん・ずんだもん等) | VOICEVOX/voicevox_vvm releases |
| `open_jtalk_dic_utf_8-1.11/` | r9y9/open_jtalk releases |

## クレジット・ライセンス

- 音声: **VOICEVOX:四国めたん**(公開時はこのクレジット表記が必要。動画の最後と概要欄に記載)
- フォント: M PLUS Rounded 1c(SIL Open Font License 1.1)
- BGM: 自作(外部音源不使用)
