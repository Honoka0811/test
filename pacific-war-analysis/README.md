# 太平洋戦争 日米戦力差の推移 — ショート動画

1941年12月の開戦から1945年8月の終戦まで、日本と米国の戦力差がどう推移したかを
数字で追う縦型ショート動画(1080×1920 / 30fps / 約72秒)です。字幕に加え、男性音声(VOICEVOX:青山龍星)のナレーション付き版があります。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/チェックリストの `metadata.md`)
- 完成動画(男性ナレーション付き): `output/pacific_war_power_gap_narrated.mp4`
- 完成動画(無音・字幕のみ): `output/pacific_war_power_gap.mp4`
- ナレーション音声のみ: `output/narration.wav`
- BGMのみ: `output/bgm.wav`(自作・権利フリー)
- サムネイル: `output/thumbnail.png`

## 構成(約72秒)

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00–0:08 | タイトル | 太平洋戦争 日米戦力差の推移 1941→1945 |
| 0:08–0:17 | 開戦時の国力 | GDP ×5.6 / 鉄鋼 ×11 / 石油 ×540 |
| 0:17–0:25 | 海軍力は日本優位 | 空母 日本10隻 vs 米国7隻(太平洋3隻) |
| 0:25–0:37 | 航空機生産の推移 | 1941–45年 年間生産機数、累計 約7万機 vs 約31万機 |
| 0:37–0:49 | 空母保有数の推移 | 1943年に逆転、以後一方的に拡大 |
| 0:49–0:58 | 日本の商船保有量 | 640万t → 150万t、石油備蓄の枯渇 |
| 0:58–1:07 | 量の差が質の差へ | 搭乗員の飛行時間、マリアナ沖海戦の損失比 |
| 1:07–1:11 | まとめ | 3つのポイント + 出典 |

## 使用データ(概数)

| 項目 | 日本 | 米国 | 主な出典 |
|---|---|---|---|
| GDP 1941年(1990年国際ドル) | 約1,960億 | 約1兆940億 | M. Harrison, *The Economics of World War II* (1998) |
| 鉄鋼生産 1941年 | 約680万t | 約7,500万t | 同上ほか |
| 石油生産 1941年(国内) | 約260万バレル | 約14億バレル | USSBS ほか |
| 航空機生産 1941–45年 | 5,088 / 8,861 / 16,693 / 28,180 / 11,066 | 26,277 / 47,836 / 85,898 / 96,318 / 49,761 | R. Overy, *Why the Allies Won* (1995), USSBS |
| 空母保有数(正規+軽, 41.12/42.12/43.12/44.12/45.8) | 10 / 7 / 9 / 5 / 4 | 7 / 4 / 18 / 25 / 28 | 各種戦史資料(就役数ベース、損傷艦含む) |
| 日本商船保有量(500総トン以上, 百万総トン) | 6.4 / 5.9 / 5.0 / 2.8 / 1.5 | — | USSBS, JANAC |
| 商船喪失 | 約880万総トン(うち約55%が米潜水艦) | — | JANAC |
| 新人搭乗員の飛行時間 | 約700h(1941) → 100h未満(1945) | 約300–400hを維持 | 各種戦史資料 |
| マリアナ沖海戦 航空機損失 | 約300機 | 約30機(空戦) | 各種戦史資料 |

数値はいずれも資料によって幅があるため概数として扱っています。動画内にも「概数」と明記しています。

## 再生成の方法

```bash
cd pacific-war-analysis
node capture.js            # output/pacific_war_power_gap.mp4 (無音版) を生成
python3 narrate.py         # ナレーション合成 + BGM ミックスで output/pacific_war_power_gap_narrated.mp4 を生成
python3 bgm.py 71.5 bgm.wav # BGM だけを書き出す場合
./export_upload.sh         # upload/ にアップロード用一式を書き出す(-14 LUFS 正規化・ステレオAAC・SRT・JPG)
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し、ffmpeg(libx264)にパイプして mp4 化
- `bgm.py` … ドキュメンタリー風BGM(Dマイナー、72BPM。低音ドローン+倍音パッド+和太鼓風の打音+まばらなアルペジオ+簡易リバーブ)を numpy だけで合成。外部音源を使わないため権利表記は不要
- `narrate.py` … シーンごとの原稿を VOICEVOX(話者: 青山龍星 ノーマル, style 13)で合成し、各シーンの長さに収まるよう話速を自動調整。BGM はナレーション中に自動で音量を下げて(ダッキング: 無音時 約-28 LUFS、発話時 約-35 LUFS)ミックスし、動画に合成。`voicevox_core` が無い環境では Open JTalk にフォールバック
- 必要なもの: Node.js, `playwright`(Chromium), `ffmpeg`, 日本語フォント(IPAゴシック), Python 3 + `numpy` + `pyopenjtalk`(辞書用)

### VOICEVOX のセットアップ(ナレーション用)

VOICEVOX CORE の GitHub リリースから次を取得し、環境変数でパスを渡します。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| Python ラッパー `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `15.vvm`(青山龍星)、`4.vvm`(玄野武宏) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 同梱のものを自動使用 | `VOICEVOX_DICT`(任意) |

話者を変える場合は `VOICEVOX_STYLE=11 python3 narrate.py`(11 = 玄野武宏)のようにします。
VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:青山龍星」のクレジット表記が必要です(動画の最後のカードに記載済み)。

ナレーションの原稿は `narrate.py` の `SCRIPT` にあり、書き換えて再実行すれば差し替えられます。

色は日本=赤 `#E8524F`、米国=青 `#3F8DE8` の2系列固定。色覚多様性(P型/D型/T型)での分離を検証済みです。
