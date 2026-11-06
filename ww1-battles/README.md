# 第一次世界大戦 激戦の一覧 — ショート動画

第一次世界大戦(1914–1918)の主な激戦8つを、年代順に地図・数字・ナレーションで紹介する縦型ショート動画です
(1080×1920 / 30fps / 約80秒)。

- BGM: J.S.バッハ「G線上のアリア」(管弦楽組曲第3番 BWV 1068 より「エア」)
  演奏: アメリカ空軍バンド(United States Air Force Band)。米国連邦政府の著作物のため **パブリックドメイン**(17 U.S.C. §105)。
  取得元: Internet Archive `AirSuiteNo.3InDMajor` → `assets/air_usaf_band.mp3`
- ナレーション: **VOICEVOX:青山龍星**(ノーマル, style 13)
- フォント: Noto Serif JP(SIL Open Font License, `assets/OFL.txt`)
- 地図: Natural Earth 1:50m 陸地データ(パブリックドメイン, world-atlas 経由)→ `assets/land_europe.js`

## 構成

| # | シーン | 主な数字(概数) |
|---|---|---|
| 0 | タイトル「第一次世界大戦 激戦の一覧」 | 8つの戦場を地図上に表示 |
| 1 | タンネンベルクの戦い(1914.8 東部戦線) | 死傷・捕虜 約18万人、捕虜 約9万人 |
| 2 | 第一次マルヌ会戦(1914.9 西部戦線) | 死傷 約50万人 |
| 3 | ガリポリの戦い(1915.4–1916.1) | 死傷 約50万人 |
| 4 | ヴェルダンの戦い(1916.2–12) | 死傷 約70万人(仏 約38万 / 独 約34万) |
| 5 | ユトランド沖海戦(1916.5–6) | 戦死 約8,600人、沈没 英14隻 / 独11隻 |
| 6 | ソンムの戦い(1916.7–11) | 死傷 100万人以上、初日の英軍死傷 約5万7千 |
| 7 | パッシェンデールの戦い(1917.7–11) | 死傷 約50万人(推計の幅が大きい)、前進 約8km |
| 8 | アミアンの戦い(1918.8) | 死傷・捕虜 約12万人、戦車500両以上 |
| 9 | まとめ(一覧+比較バー) | 兵士の死者 約900万人 |

数値はいずれも資料によって幅があるため概数として扱い、画面にも「概数・推計」と明記しています。
主な参照: 各戦いの英語版 Wikipedia 記事とその出典、Imperial War Museums、Commonwealth War Graves Commission の解説など。

## 生成方法

```bash
cd ww1-battles
./make.sh          # 下の 1〜5 を順に実行
```

1. `python3 narrate.py` … `scenes.js` の原稿を VOICEVOX で1文ずつ合成。実測した長さからシーン尺を決め、
   `output/narration.wav`・`output/timings.json`・`output/subtitles_ja.srt` を出力
2. `node capture.js` … `render.html` を 1 フレームずつ撮影して `output/video_silent.mp4`(timings.json に同期)
3. `python3 mix.py` … アリアをナレーション中だけ自動で下げて(ダッキング)ミックスし `output/ww1_battles.mp4`
4. サムネイル: `THUMB=1 node capture.js --stills 4.5`(字幕なしの静止画)
5. `./export_upload.sh` … -14 LUFS に正規化して `upload/` に最終 mp4・SRT・JPG を書き出し

- 原稿・数字・地図上の位置はすべて `scenes.js` にあり、書き換えて再実行すれば反映されます
- `render.html` はブラウザで開くとプレビュー再生します(ナレーション未生成時は推定タイミング)
- `node capture.js --stills 3,12,40` で任意の時刻の静止画を `output/` に書き出せます

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.16.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| `15.vvm`(青山龍星) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS` |
| Open JTalk 辞書 | `pip install pyopenjtalk` 同梱のものを自動使用 | `VOICEVOX_DICT`(任意) |

既定パスは `/home/user/vv/ort/...` と `/home/user/vv/vvms`。話速は `VOICE_SPEED=1.1 python3 narrate.py` のように変更できます。
VOICEVOX の音声を公開する場合は「VOICEVOX:青山龍星」のクレジット表記が必要です(動画末尾と説明文に記載)。
