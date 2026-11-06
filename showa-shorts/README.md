# 昭和の当たり前 BEST5 — YouTube ショート動画

「今じゃ考えられない！昭和の常識」をランキング形式で紹介する縦型ショート(1080×1920 / 30fps / 55秒)。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイル・タイトル/説明文/タグ/固定コメント/チェックリストの `metadata.md`)
- ナレーション: **VOICEVOX:四国めたん**(ノーマル/あまあま/ツンツンをセリフごとに使い分け)
- BGM: 昭和歌謡風(128BPM・Am→第1位で全音転調)をプログラムで自作合成。効果音も自作(権利フリー)
- フォント: Dela Gothic One / Mochiy Pop One(SIL Open Font License 1.1)

## 構成
| 時間 | 内容 |
|---|---|
| 0:00–0:07 | フック「昭和では当たり前。でも令和なら大炎上!?」→ 伏せカード5枚 |
| 0:07–0:15 | 第5位 飛行機の中でタバコが吸えた(男性喫煙率83.7%・1966年) |
| 0:15–0:23 | 第4位 買い物に消費税がなかった(導入は1989年4月) |
| 0:23–0:31 | 第3位 駅員さんが切符にハサミ(カチカチ音の効果音) |
| 0:31–0:39 | 第2位 電話は家に1台だけ(黒電話のベル) |
| 0:39–0:43 | 溜め「第1位は…」(BGM停止・ドラムロール) |
| 0:43–0:50 | 第1位 土曜日も学校があった=半ドン(転調・紙吹雪・チャイム) |
| 0:50–0:55 | 「いくつ知ってた?」チェックリスト → コメント誘導 |

## 再生成
```bash
python3 narrate.py      # VOICEVOX でナレーション合成 → output/timeline.json(シーン尺はセリフ長から自動決定)
node capture.js         # render.html を撮影 → output/video_silent.mp4
python3 mix.py          # BGM + 効果音 + ダッキング → output/showa_best5.mp4
./export_upload.sh      # -14 LUFS 正規化 → upload/
```
原稿を変えたいときは `narrate.py` の `SCENES` を編集して上から順に再実行するだけで、映像のタイミングも追従します。

必要なもの: voicevox_core 0.16 (Python) + voicevox_onnxruntime 1.17.3 + `0.vvm`(四国めたん)、pyopenjtalk-plus、numpy、scipy、Playwright(Chromium)、ffmpeg。
パスは環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVMS` / `VOICEVOX_DICT` で指定できます。
