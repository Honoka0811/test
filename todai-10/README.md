# 東京大学のここがすごい！10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約64秒)。ナレーションは **VOICEVOX:四国めたん**(ノーマル)、BGMは numpy で合成したオリジナル曲(権利フリー)。

- **完成動画: `output/todai_sugoi_10.mp4`**(-14 LUFS 正規化・ステレオAAC)
- サムネイル: `output/thumbnail.jpg`
- 字幕: `output/subtitles_ja.srt`
- ナレーション単体: `output/narration.wav`

## 構成

| No. | 項目 | 画面の数字 |
|---|---|---|
| — | タイトル「東京大学のここがすごい！10選」 | |
| 1 | 日本最初の近代大学(東京開成学校+東京医学校) | 1877年 創立 |
| 2 | ノーベル賞受賞者(卒業生) | 10人以上 |
| 3 | 総理大臣の出身大学 | 歴代最多 |
| 4 | 赤門(加賀藩前田家・重要文化財) | 1827年 建立 |
| 5 | 安田講堂(安田善次郎の寄付) | 1925年 完成 |
| 6 | 土地面積(演習林含む) | 約326km²(東京23区の約半分) |
| 7 | 小石川植物園(小石川御薬園がルーツ・日本最古の植物園) | 1684年 起源 |
| 8 | スーパーカミオカンデ/ニュートリノ研究 | 2度のノーベル賞(小柴2002・梶田2015) |
| 9 | 進学選択(全員が教養学部で入学) | 2年生で学部を決める |
| 10 | 世界大学ランキング | 国内1位 |
| — | 締め「一番すごいのは何番？コメントで教えてね！」 | |

数値は概数。投稿前に最新の公式情報(東京大学の概要・各ランキング)で確認してください。

## 投稿用メタデータ案

- タイトル: `東京大学のここがすごい！10選 #東大 #東京大学 #shorts`
- 説明文:
  ```
  日本最古の近代大学・東京大学のすごいところを10個紹介！
  あなたが一番すごいと思ったのは何番？コメントで教えてね！

  ※数値は概数です
  ナレーション: VOICEVOX:四国めたん
  BGM: オリジナル
  ```
- タグ: 東京大学, 東大, 大学, 受験, 雑学, 赤門, 安田講堂, VOICEVOX, 四国めたん

> VOICEVOX の利用規約により、動画の説明文などに「VOICEVOX:四国めたん」のクレジット表記が必要です(動画内にも表示済み)。

## 再生成

```bash
cd todai-10
python3 narrate.py   # 原稿(content.py)→ ナレーション合成・シーン尺(timeline.json)・字幕SRT
node capture.js      # render.html を撮影 → output/video_silent.mp4
python3 mix.py       # BGM(bgm.py)をダッキングしてミックス・-14 LUFS 正規化 → output/todai_sugoi_10.mp4
node capture.js --still 12.5 frame.png   # 任意時刻の静止画プレビュー
```

台本の修正は `content.py`(読み上げ文と字幕文)と `render.html` の `ITEMS`(画面表示)の2か所。
シーンの長さはナレーションの長さから自動で決まります。

VOICEVOX CORE 0.16.2(Python wheel)・ONNX Runtime・`0.vvm`・Open JTalk 辞書を `/home/user/vv/` に置いて実行します(パスは環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVM` / `VOICEVOX_DICT` で変更可)。

## 素材とライセンス

- 音声: VOICEVOX:四国めたん
- BGM: `bgm.py` で生成したオリジナル(Cメジャー/118BPM)
- フォント: M PLUS Rounded 1c(SIL Open Font License 1.1, `fonts/OFL.txt`)
- イラスト: すべて canvas で描画したオリジナル(写真・ロゴ不使用)
