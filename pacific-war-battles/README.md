# 太平洋戦争の激戦 一覧 — ショート動画

太平洋戦争の主要な激戦7つを、地図と数字で時代順にたどる縦型ショート動画(1080×1920 / 30fps / 約82秒)。
ナレーション: VOICEVOX:青山龍星、BGM: J.S.バッハ「G線上のアリア」(BWV1068)を自前で弦楽合奏風に合成。

- **アップロード用一式: `upload/`**(`pacific_war_battles_final.mp4`・字幕SRT・サムネイル・`metadata.md`)
- ナレーション付き(正規化前): `output/pacific_war_battles_narrated.mp4` / 無音版: `output/pacific_war_battles.mp4`
- 音声単体: `output/narration.wav`、`output/bgm.wav`

## 構成

| # | 戦い | 時期 | 画面の数字(概数) |
|---|---|---|---|
| 1 | ミッドウェー海戦 | 1942年6月 | 日本 空母喪失4隻・戦死約3,000人 / 米国 空母喪失1隻 |
| 2 | ガダルカナル島の戦い | 1942年8月〜43年2月 | 日本 死者約2万人(うち餓死・病死約1.5万人)/ 米国 戦死約7,000人 |
| 3 | マリアナ沖海戦 | 1944年6月 | 日本 空母喪失3隻・航空機約400機 / 米国 航空機約120機 |
| 4 | サイパン島の戦い | 1944年6〜7月 | 日本 戦死約3万人 / 民間人 約1万人 / 米国 戦死約3,400人 |
| 5 | レイテ沖海戦 | 1944年10月 | 日本 艦艇喪失約30隻・戦死約1万人 / 米国 艦艇喪失6隻 |
| 6 | 硫黄島の戦い | 1945年2〜3月 | 日本 戦死約2万人 / 米国 戦死約6,800人・死傷約2.6万人 |
| 7 | 沖縄戦 | 1945年3〜6月 | 日本 軍人・軍属約9.4万人 / 一般住民約9.4万人 / 米国 戦死約1.25万人 |

数値は資料により幅があるため概数(画面にも明記)。沖縄戦は沖縄県援護課の集計、そのほかは防衛庁『戦史叢書』や各種戦史資料の一般的な値。

## 素材と権利

| 素材 | 出典 | 権利 |
|---|---|---|
| BGM | 楽譜データ: Mutopia Project「Air, from Suite No.3 in D」トロンボーン四重奏版 MIDI(arr. Ross Keenum, `assets/air-tromb.mid`)。音は `bgm_air.py` が numpy で合成 | パブリックドメイン(作曲・楽譜とも)。既存録音は不使用 |
| ナレーション | VOICEVOX CORE + 青山龍星(style 13) | 公開時「VOICEVOX:青山龍星」のクレジット必須(動画末尾・説明文に記載) |
| 地図 | Natural Earth 1:50m(npm `world-atlas`) | パブリックドメイン |

## 再生成

```bash
python3 narrate.py          # ナレーション合成 → output/narration.wav, subtitles_ja.srt, timeline.js(シーン尺)
node make_map.js            # 地図データ → assets/map.js(要 world-atlas, topojson-client。生成済み)
node capture.js             # render.html を1フレームずつ撮影 → output/pacific_war_battles.mp4
python3 mix.py              # BGM合成 + ダッキングミックス → output/pacific_war_battles_narrated.mp4
./export_upload.sh          # -14 LUFS 正規化 + リミッター → upload/
```

必要なもの: Node.js + playwright, ffmpeg, IPAゴシック, Python3 + numpy, scipy, mido, voicevox_core 0.16, pyopenjtalk(辞書)。
VOICEVOX のセットアップは `../pacific-war-analysis/README.md` と同じ(`VOICEVOX_ORT` / `VOICEVOX_VVMS` 環境変数)。
原稿は `narrate.py` の `SCRIPT`(読み上げ用テキストと字幕テキストを別々に持つ)。尺はナレーションの長さから自動で決まり、BGM は 48 BPM(`BGM_BPM` 環境変数で変更可)。動画に曲全体が収まらない場合は、最後の約5秒でフェードアウトする(現在は76拍中66拍目付近まで)。
