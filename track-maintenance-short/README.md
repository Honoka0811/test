# 保線作業員のお仕事 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約64秒)。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGMは自作(numpy合成・権利フリー)。字幕は画面に焼き込み済み。

- **完成動画: `upload/track_maintenance_final.mp4`**(-14 LUFS 正規化・ステレオAAC)
- 字幕SRT: `upload/subtitles_ja.srt` / サムネイル: `upload/thumbnail.jpg`
- ナレーションのみ `output/narration.wav`、BGMのみ `output/bgm.wav`、無音版 `output/track_maintenance.mp4`

## 構成

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00 | タイトル | 線路のお医者さん「保線作業員のお仕事」 |
| 0:08 | 01 保線ってなに? | レール・枕木・バラストの断面図 |
| 0:17 | 02 仕事は夜 | 終電〜始発の間のわずか数時間(時刻は一例) |
| 0:25 | 03 点検 | 徒歩巡回 / ハンマーでの打音検査 / 検測車でミリ単位の測定 |
| 0:35 | 04 補修 | マルチプルタイタンパーでの突き固め、レール・枕木交換 |
| 0:44 | 05 安全第一 | 見張り員 / 指差し確認 / 工具の数の確認 |
| 0:55 | 朝 | 始発列車が走り出す + クレジット |

## 再生成

```bash
node capture.js          # render.html を撮影して無音版 mp4
python3 narrate.py       # 四国めたんのナレーション合成 + BGM ダッキングミックス
./export_upload.sh       # upload/ に最終版を書き出し
```

VOICEVOX は `voicevox_core`(0.16.3 wheel)、ONNX Runtime 1.17.3、音声モデル `0.vvm`(四国めたん)、Open JTalk 辞書を
`/home/user/vv/` 以下に置いて使用(パスは環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVMS` / `VOICEVOX_DICT` で変更可)。
公開時は利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画末尾に記載済み)。
