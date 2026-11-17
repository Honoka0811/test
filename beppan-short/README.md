# 「別班」は実在するのか? — ショート動画

ドラマ『VIVANT』で注目された陸上自衛隊の秘密情報部隊「別班」について、政府見解と報道・証言を並べて整理する縦型ショート動画(1080×1920 / 30fps / 59秒)。

- 完成動画: `output/beppan_short.mp4`(ナレーション+BGM、-14 LUFS)
- 字幕: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg` / 原稿: `narration_script.txt`
- ナレーション: **VOICEVOX:青山龍星**(公開時はこのクレジット表記が必要。動画の最後にも表示)
- BGM: `bgm.py` が numpy だけで合成する自作のサスペンス調トラック(外部音源なし・権利表記不要)

## 構成

| シーン | 内容 |
|---|---|
| 1 フック | 「別班」は実在するのか? |
| 2 政府の公式見解 | 2013年12月10日の答弁書と、2026年7月28日の防衛相会見での否定 |
| 3 2013年11月の報道 | 共同通信の報道(首相・防衛相に知らせず海外で情報活動) |
| 4 ルーツ | 1950年代の日米合同情報訓練 → 通称「ムサシ機関」 |
| 5 証言 | 陸上幕僚長経験者・情報本部長経験者の証言(石井暁氏の取材) |
| 6 結論 | 公式には存在しない。しかし証言は消えていない |

## 出典

- 参議院 質問主意書・答弁書(第185回国会 質問第77号、答弁書 2013年12月10日):「これまで自衛隊に存在したことはなく、現在も存在していない」
  https://www.sangiin.go.jp/japanese/joho1/kousei/syuisyo/185/touh/t185077.htm
- 小泉進次郎防衛相 2026年7月28日会見(J-CAST ニュース) https://www.j-cast.com/2026/07/29516720.html
- 石井暁『自衛隊の闇組織 秘密情報部隊「別班」の正体』(講談社現代新書)の抜粋記事
  https://president.jp/articles/-/73719 / https://president.jp/articles/-/73723 / https://gendai.media/articles/-/57914

報道・証言の部分は「〜と報じた」「〜とされる」という伝聞の形で扱っている。政府は一貫して存在を否定している。

## 再生成

```bash
./build.sh   # npm install → narrate.py → capture.js → 音量正規化して output/beppan_short.mp4
```

- `script.py` … 台本(字幕表示・読み上げ・強調語)。ここを書き換えて `./build.sh` すれば尺・字幕・映像のタイミングが自動で追従する
- `narrate.py` … VOICEVOX で合成し、ポーズ位置から字幕タイミング(`output/timings.json`)を算出。BGM をナレーション中だけ下げてミックス
- `render.html` + `capture.js` … Canvas で時刻 t のフレームを描画し、Playwright で 1 フレームずつ撮影
- 必要なもの: Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + pyopenjtalk + voicevox_core 0.17.1。VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ(`VOICEVOX_ORT` / `VOICEVOX_VVMS`)
