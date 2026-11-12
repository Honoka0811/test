# 食品サンプル職人 — ショート動画

食品サンプル職人の仕事(歴史・産地・4つの工程・レタスの職人ワザ)を紹介する縦型ショート動画(1080×1920 / 30fps / 約69秒)。

- **アップロード用: `upload/food_sample_artisan_final.mp4`**(-14 LUFS 正規化・ステレオAAC)、`upload/subtitles_ja.srt`、`upload/thumbnail.jpg`
- ナレーション: VOICEVOX:四国めたん(ノーマル)— 公開時は動画説明欄にも「VOICEVOX:四国めたん」とクレジットを記載すること
- BGM: `bgm.py` でプログラム合成した自作曲(Fメジャー・112BPM、マリンバ+グロッケン+ベース+シェイカー)
- フォント: Zen Maru Gothic(SIL Open Font License)

## 構成

| 時間 | 内容 |
|---|---|
| 0:00 | タイトル「本物より、おいしそう。」ショーケース |
| 0:07 | はじまりは「ろう」→ いまは樹脂 |
| 0:15 | 岐阜県郡上市で国内生産の約6割 |
| 0:23 | STEP1 型取り(シリコン) |
| 0:30 | STEP2 樹脂を流し込み・加熱 |
| 0:37 | STEP3 色付け(エアブラシ・筆・照り) |
| 0:45 | STEP4 盛り付け(湯気・持ち上げ麺) |
| 0:53 | 職人ワザ:お湯にろうを垂らしてレタスづくり |
| 1:02 | まとめ・クレジット |

## 再生成

```bash
node capture.js      # output/food_sample_artisan.mp4(無音)
python3 narrate.py   # ナレーション合成 + BGM ダッキング → output/food_sample_artisan_narrated.mp4
```
VOICEVOX は voicevox_core 0.16.2 + 0.vvm(四国めたん)+ voicevox_onnxruntime 1.17.3 を使用(パスは narrate.py 冒頭の環境変数参照)。
