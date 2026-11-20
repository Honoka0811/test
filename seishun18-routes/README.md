# 青春18きっぷで巡るおすすめルート5選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約78秒)。ナレーションは **VOICEVOX:四国めたん(ノーマル)**、BGM は numpy で合成した自作曲です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `metadata.md`)
- 完成動画: `output/seishun18_routes.mp4`/ナレーションのみ: `output/narration.wav`

## 構成

| シーン | 内容 |
|---|---|
| タイトル | 青春18きっぷで巡る おすすめルート5選(案内:四国めたん) |
| 1 東海道本線 | 東京→大阪 約556km・普通列車で約9時間・運賃約9千円分 |
| 2 五能線 | 快速リゾートしらかみ(指定席券で乗車可)・日本海・千畳敷 |
| 3 只見線 | 2022年10月全線再開・第一只見川橋梁・本数が少ない |
| 4 予土線 | 四万十川・しまんトロッコ/ホビートレイン・沈下橋 |
| 5 山陰本線 | 日本一長い在来線(約674km)・餘部橋梁・宍道湖・2日がかり |
| 基本ルール | 3日間用10,000円/5日間用12,050円・連続日・特急/新幹線不可 |
| エンド | ルート一覧+「コメントで教えてね」+クレジット |

距離・所要時間・運賃は概算。きっぷのルールは2024年冬季以降のもの(投稿前にJR公式で要確認)。

## 再生成

```bash
python3 narrate.py   # 四国めたんで音声合成 → output/narration.wav, output/subtitles_ja.srt, timing.js(シーン尺を音声長から自動決定)
node capture.js      # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py       # BGM(bgm.py)をダッキングしてミックス、-14 LUFS 目標で正規化 → output/seishun18_routes.mp4
node thumbnail.js    # output/thumbnail.png
```

- 原稿は `narrate.py` の `SCRIPT`(読み上げ用と字幕用の2表記)。書き換えて上の順に再実行すれば、尺も字幕も自動で追従します。
- VOICEVOX CORE 0.16.1 + ONNX Runtime 1.17.3 + 音声モデル `0.vvm`(四国めたん)。パスは `VOICEVOX_ORT` / `VOICEVOX_VVMS` で指定(セットアップは `../pacific-war-analysis/README.md` と同じ手順)。スタイル変更は `VOICEVOX_STYLE`(2=ノーマル, 0=あまあま, 6=ツンツン)。
- フォント: M PLUS Rounded 1c(SIL OFL、`fonts/LICENSE`)。
- 公開時は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画末尾と説明文に記載済み)。
