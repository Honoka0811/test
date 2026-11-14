# 男性が女性より多く払うべき理由 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約55秒)。ナレーションは VOICEVOX:青山龍星、BGM はプログラムで作った自作曲(権利フリー)。

- 完成動画: `output/men_pay_more.mp4`
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.png`
- ナレーションのみ: `output/narration.wav` / BGM のみ: `output/bgm.wav`

## 構成

| シーン | 内容 |
|---|---|
| タイトル | 男性が女性より多く払うべき理由(4つ紹介) |
| 理由① 収入の差 | 女性の平均賃金は男性の約76%(月36.3万円 vs 27.5万円、令和6年 賃金構造基本統計調査) |
| 理由② 身だしなみコスト | 化粧品・美容院・ネイル/脱毛・服 |
| 理由③ ライフイベント | 女性の正規雇用率の L字カーブ(概数) |
| 理由④ 安全のためのお金 | 深夜のタクシー・オートロック物件・防犯グッズ |
| まとめ | 正解はカップルそれぞれ。大切なのは二人の納得感 |
| エンド | あなたはどう思う? + クレジット |

## 再生成

```bash
python3 narrate.py voice   # ナレーション合成 → シーン尺(output/timings.json)・字幕を決定
node capture.js --stills   # 確認用の静止画とサムネイル
node capture.js            # 無音の映像 output/video_silent.mp4
python3 narrate.py mix     # BGM をダッキングしながらミックス → output/men_pay_more.mp4(-14 LUFS 目標)
```

ナレーション原稿は `narrate.py` の `SCRIPT`。VOICEVOX CORE 0.16.1 / ONNX Runtime 1.17.3 / `15.vvm`(青山龍星)を使用(セットアップは `../pacific-war-analysis/README.md` 参照)。
公開時は「VOICEVOX:青山龍星」のクレジット表記が必要です(エンドカードに記載済み)。
