# 奇跡の鉱物の栄枯盛衰 — アスベストとジョンズ・マンビル

「奇跡の鉱物」と呼ばれたアスベストと、世界最大級のアスベスト企業ジョンズ・マンビルの栄光と転落をたどる
縦型動画(1080×1920 / 30fps / 2分49秒)。ナレーションは VOICEVOX:四国めたん、BGM は自作(numpy 合成)。

- 完成動画: `output/asbestos_rise_and_fall.mp4`
- アップロード用のタイトル・説明文・タグ: `output/metadata.md`
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg` / ナレーションのみ: `output/narration.wav`

## 作り方

```bash
python3 narrate.py   # script.json → 四国めたんで合成。output/narration.wav と timeline.js(実測タイミング)を出力
node capture.js      # render.html を 1 フレームずつ描画して output/video_silent.mp4 に(4 並列、約 5 分)
python3 mix.py       # BGM 合成 + ダッキング + -14 LUFS 正規化 → output/final.mp4
ffmpeg -i output/final.mp4 -c:v libx264 -preset slow -crf 24 -maxrate 6M -bufsize 12M -c:a copy -movflags +faststart output/asbestos_rise_and_fall.mp4
```

- `script.json` … 原稿。`/` は字幕の区切り、`[...]` は強調、`read` は読みの上書き
- `render.html` … Canvas 2D。`render(t)` が時刻 t のフレームを決定論的に描く。ブラウザで開くとプレビュー(`?t=60` で頭出し)
- `node capture.js --shots 5,30,90` … 指定秒の静止画を `output/shots/` に書き出して確認
- 原稿を変えたら上の 4 コマンドを順に再実行する(映像のタイミングは音声に自動で追従。ただし `render.html` は行番号で演出を割り当てているので、行の追加・削除時は `LT(n)` / `CT(n, m)` の番号も合わせる)

### 必要なもの
Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + pyopenjtalk、VOICEVOX CORE 0.17.1
(`voicevox_core` の whl、`voicevox_onnxruntime` 1.17.3、音声モデル `0.vvm`)。パスは `VOICEVOX_ORT` / `VOICEVOX_VVMS` で指定。
フォントは Noto Sans JP と しっぽり明朝 B1(どちらも SIL OFL、`fonts/` に同梱)。

## 主な事実と出典(概数)
| 内容 | 出典 |
|---|---|
| 1858年創業、1901年合併でジョンズ・マンビルに。1930〜1982年ダウ平均構成銘柄 | 同社沿革、ダウ平均の歴代構成銘柄 |
| 1935年10月1日の書簡 "the less said about asbestos, the better off we are"(レイベストス・マンハッタン社長 → J-M 社顧問弁護士) | 米国の判決文での引用 |
| 1964年 セリコフらの疫学調査(JAMA)、1973年 Borel v. Fibreboard(第5巡回区控訴裁) | 論文・判決 |
| 1982年8月26日 チャプター11申請。係争中約16,500件、将来賠償見込み約20億ドル超、フォーチュン500の181位 | Time、Washington Post、UPI(1982年) |
| 1988年再建(補償基金が株式の最大約80%)、2001年バークシャー・ハサウェイが買収 | 同社沿革、バークシャー年次報告 |
| 世界生産のピークは1977年・約479万トン | USGS Circular 1298、Mineral Commodity Summaries |
| 日本の累計輸入 約1,000万トン(ピーク1974年 約35万トン)、約8割が建材。繊維は髪の毛の約1/5000、用途は約3,000種 | 環境再生保全機構、環境省 |
| 2005年6月 クボタ旧神崎工場周辺の住民被害が判明。2006年原則禁止、2012年全面禁止 | 報道、厚生労働省 |
| 中皮腫死亡 1995年500人 → 2021年1,635人、2024年1,562人 | 厚生労働省 人口動態統計 |

創業者の死因は「肺の病」と伝えられ、石綿が原因とみられていますが、当時の一次資料で病名までは確認できていません(動画でも「みられています」と表現)。
日本の輸入量グラフのうちピーク年以外の年次の値は概略です。
