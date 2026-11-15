# 北海道大学のここがすごい！10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約53秒)。ナレーションは **VOICEVOX:四国めたん(ノーマル)**、BGM は numpy で合成したオリジナル曲(権利フリー)。

- 完成動画: `output/hokudai_sugoi_top10.mp4`(-14 LUFS 前後に正規化済み・ステレオ AAC)
- 字幕: `output/subtitles_ja.srt`

## 10選

| No. | 内容 | 画面の見出し |
|---|---|---|
| 1 | JR札幌駅から正門まで徒歩約7分 | 徒歩7分 |
| 2 | 札幌キャンパス約177ha = 東京ドーム約38個分 | 東京ドーム38個分 |
| 3 | 研究林などを含めた総面積 約660km²(東京23区 約627km²より広い) | 約660km² |
| 4 | 1876年 札幌農学校として創基、2026年で150周年 | 1876年 創基 |
| 5 | 初代教頭 W.S.クラーク博士「Boys, be ambitious!」 | Boys, be ambitious! |
| 6 | 旧5千円札の新渡戸稲造は札幌農学校の出身 | 旧5千円札の顔 |
| 7 | 2010年 鈴木章 名誉教授がノーベル化学賞 | ノーベル化学賞 |
| 8 | 総合入試で入学後に学部を選べる | 総合入試 |
| 9 | 北13条のイチョウ並木(約70本・約380m) | イチョウ並木 |
| 10 | 総合博物館は入場無料 | 入場無料 |

公開時は概要欄に「VOICEVOX:四国めたん」のクレジットを入れてください(動画の最後にも表記済み)。

## 再生成

```bash
python3 tts.py      # ナレーション合成 → output/narration.wav, timeline.json/js, subtitles_ja.srt
node capture.js     # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py      # BGM 合成 + ダッキング + ラウドネス正規化 → output/hokudai_sugoi_top10.mp4
```

- 原稿は `tts.py` の `SCRIPT`(読み上げ用, 字幕用)。シーンの長さはナレーションの長さから自動で決まる
- 画面の見出し・アイコンは `render.html` の `ITEMS`
- BGM は `bgm.py`(Fメジャー / 118BPM のポップ調)
- VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ(音声モデルは `0.vvm` = 四国めたん。`VOICEVOX_STYLE` 既定 2 = ノーマル、0 = あまあま, 6 = ツンツン)
