# 食品サンプル職人 — ショート動画

食品サンプル職人の仕事(歴史・産地・4つの工程・レタスの職人ワザ)を紹介する縦型ショート動画(1080×1920 / 30fps / 約107秒)。

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
| 1:02 | 海外へも輸出(香港・シンガポール)、訪日客のお土産 |
| 1:11 | 業界最大手:いわさきグループ(1932年創業・本社 郡上市) |
| 1:20 | 年収の目安:会社員で約300万〜500万円、求人は月給20万円台中心 |
| 1:29 | 職人になるには:資格不要 → 体験教室 → メーカー就職 → 見習い修業 |
| 1:40 | まとめ・クレジット |

## 参考にした情報(2026年11月時点で確認)

- 郡上市の全国シェア約6割・1932年創業・郡上八幡工場: [旅色 サンプルビレッジ・いわさき](https://tabiiro.jp/leisure/s/200067-gujo-iwasakimokei/)、[いわさきグループについて](https://www.foodmodel.com/about/)
- いわさきグループ(いわさき・岩崎・岩崎模型製造)が業界最大手: [いわさきグループについて](https://www.foodmodel.com/about/)、[イワサキ・ビーアイ](https://www.iwasaki-bei.co.jp/archives/396)
- 香港・シンガポールへの輸出: [JETRO 岩崎模型製造の事例](https://www.jetro.go.jp/case_study/2019/iwasakimokei.html)
- 訪日客のお土産需要: [訪日ラボ(まいづる 海外販売)](https://honichi.com/news/2018/11/06/shokuhin-sampuru/)
- 年収の目安(300万〜500万円)・求人の月給: [wovie 転職コラム](https://wovie.me/contents/column/?p=107441)、[joboon](https://joboon.jp/job/2358/)、求人サイト各種
- 年収・シェアは公的統計ではなく、記事・求人情報ベースの概数。動画内にも注記あり


## 再生成

```bash
node capture.js      # output/food_sample_artisan.mp4(無音)
python3 narrate.py   # ナレーション合成 + BGM ダッキング → output/food_sample_artisan_narrated.mp4
```
VOICEVOX は voicevox_core 0.16.2 + 0.vvm(四国めたん)+ voicevox_onnxruntime 1.17.3 を使用(パスは narrate.py 冒頭の環境変数参照)。
