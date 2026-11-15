# 名古屋大学のここがすごい！10選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約77秒)。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGM は numpy で合成したオリジナル曲(権利フリー)です。

- 完成動画: `output/nagoya_univ_top10.mp4`(-14 LUFS 正規化、ステレオ AAC)
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg`
- 素材: `output/narration.wav`(ナレーションのみ)、`output/bgm.wav`(BGMのみ)

## 10選

| No. | 項目 | 補足 |
|---|---|---|
| 1 | 21世紀のノーベル賞受賞者が6人 | 野依良治・小林誠・益川敏英・下村脩・赤﨑勇・天野浩 |
| 2 | 青色LEDを生んだ大学 | 2014年 ノーベル物理学賞(赤﨑勇・天野浩) |
| 3 | 最後に誕生した帝国大学 | 1939年 名古屋帝国大学(国内7番目) |
| 4 | キャンパスに地下鉄の駅 | 地下鉄名城線「名古屋大学」駅 |
| 5 | シンボルは豊田講堂 | 1960年竣工、トヨタ自動車の寄付、設計 槇文彦 |
| 6 | ノーベル賞展示館がある | 受賞者ゆかりの資料を展示 |
| 7 | 日本初の「1法人複数大学」 | 2020年 岐阜大学と東海国立大学機構を設立 |
| 8 | 指定国立大学法人 | 世界最高水準をめざす大学として選定 |
| 9 | 防災研究の拠点「減災館」 | 建物自体が免震構造 |
| 10 | 自由闊達な学風 | 名古屋大学学術憲章より |

公開前に、年や名称など事実関係を大学公式サイト等で最終確認してください。

## 再生成

```bash
python3 tts.py      # ナレーション合成 → output/narration.wav, subtitles_ja.srt, timeline.js(シーン尺)
node capture.js     # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py      # BGM(bgm.py)をダッキングしてミックス、-14 LUFS 正規化 → output/nagoya_univ_top10.mp4
python3 bgm.py 77 output/bgm.wav   # BGMのみ書き出す場合
node snap.js 2 30   # 指定秒のフレームを preview/ に PNG 保存(確認用)
```

- 原稿・見出しは `tts.py` の `SCENES`。書き換えて上の3コマンドを順に実行すれば、尺も自動で合わせ直されます。
- 話者は `VOICEVOX_STYLE`(2=ノーマル、0=あまあま、6=ツンツン、4=セクシー)で変更できます。
- VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じです(四国めたんは `0.vvm`)。Open JTalk 辞書は `VOICEVOX_DICT` で指定(既定 `/home/user/vv/open_jtalk_dic_utf_8-1.11`)。
- フォント: M PLUS Rounded 1c(SIL OFL、`fonts/OFL.txt`)。

## クレジット

公開時は利用規約に従い「VOICEVOX:四国めたん」の表記が必要です(動画内の右下とエンディングに記載済み)。
