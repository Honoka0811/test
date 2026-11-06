# アップロード用メタデータ(YouTube Shorts)

## ファイル
- 動画: `every_bounce_bigger_final.mp4`(1080×1920 / 60fps / 33.9秒 / -14 LUFS)
- サムネイル: `thumbnail.jpg`

## タイトル(英語推奨 — 言語不要の映像なので世界向けにする)
**Every Bounce = Bigger Ball 🔴 Can It Fill The Circle? #satisfying**

予備案(A/Bテスト用):
- This ball grows every time it bounces... wait for the end 😳
- 1 Bounce = +3% Size. Can It Fill The Circle?

日本語チャンネル向け: **跳ねるたびに大きくなるボール、円を埋め尽くせるか? #shorts**

## 説明文
```
Every time the ball hits the wall, it gets 3% bigger. How many bounces does it take to fill the circle? 🔴
Guess in the comments before it ends 👇

Physics simulation + sound generated with code. Every bounce plays a note.

#shorts #satisfying #physics #simulation #asmr #bouncingball
```

## タグ
satisfying, physics simulation, bouncing ball, ball grows every bounce, oddly satisfying, satisfying video, asmr, shorts, simulation, marble, circle, 物理シミュレーション, 気持ちいい動画

## 投稿設定チェックリスト
- [ ] 形式: Shorts(縦型・60秒未満 → 自動判定)
- [ ] 視聴者: 子ども向けではない(子ども向けにするとコメント不可・推薦が弱まる)
- [ ] カテゴリ: エンターテイメント
- [ ] 固定コメント: 「Guess how many bounces before it ends 👇 (answer: 71)」→ 回答コメントを誘発
- [ ] 投稿時刻: 米国東部の夕方(日本時間 朝7〜9時)が世界向けShortsの山

## 100万再生を狙う理由(設計メモ)
- **最初の1秒で問いを提示**(「円を埋められる?」)→ 結末を見たくなりスワイプされにくい
- **33.9秒・終盤に向けて加速**(後半はバウンド間隔が詰まり、音も高くなる)→ 完走率が高い
- **「Watch again?」で終わる** → ループ再生がカウントされ、視聴維持率が100%超えになりやすい
- **言葉がいらない** → 全世界のShortsフィードに乗れる
- **音・映像とも完全自作**(コードで合成)→ 著作権の申し立てリスクなし

## 伸ばし方
1本で当てるより、同じフォーマットのシリーズを毎日出すのが確実:
「ボール2個で競争」「跳ねるたびに円が縮む」「跳ねるたびにボールが増える」など。
`sim.py` の `GROW`・`R0`・`G` を変えるだけで別パターンを量産できる。
