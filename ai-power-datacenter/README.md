# AI × 電力 × 防衛 — データセンターを一番多く建てられる国はどこか(ショート動画)

「AIをどれだけ稼働させられるか = 防衛力」という観点から、2025年の各国の発電量の伸びを
「毎年建てられるデータセンターの規模(GW)」に換算して比較する縦型ショート動画
(1080×1920 / 30fps / 約70秒)です。ナレーションは VOICEVOX:青山龍星(ノーマル)。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/チェックリストの `metadata.md`)
- 完成動画(ナレーション+BGM付き): `output/ai_power_datacenter_narrated.mp4`
- 完成動画(無音・字幕のみ): `output/ai_power_datacenter.mp4`
- ナレーション音声のみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`(自作・権利フリー)
- サムネイル: `output/thumbnail.png`

## 構成(約70秒)

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00–0:07 | フック | AIの戦争は、電力の戦争。 |
| 0:07–0:16 | ものさし | DC 1GW = 年8.8TWh = 原発1基フル稼働 |
| 0:16–0:27 | 2025年に増えた電力 | 中国 +503TWh / 米国 +131 / インド +49 / EU・日本 ほぼ0 |
| 0:27–0:38 | 年間建設可能DC | 中国 50〜60GW / 米国 10〜15 / インド・EU 3〜5 / 日本 1〜2 |
| 0:38–0:48 | 米国の壁 | 13地域送電網のうち8つが予備率臨界以下、接続待ちが上限 |
| 0:48–0:58 | 日本 | 新規電源ほぼゼロ、原発1基再稼働 = DC約1GW |
| 0:58–1:10 | 結論 | 中国 ≫ 米国 > インド ≒ EU > 日本。中国は米国の4〜5倍、日本は1/10以下 |

## 使用データ(概数)

| 項目 | 値 | 出典 |
|---|---|---|
| 世界の電力需要 2025年 | 31,779 TWh(+849 TWh) | Ember, Global Electricity Review 2026 |
| 中国の需要増 2025年 | +503 TWh(需要 10,573 TWh、風力+太陽光で +474 TWh) | 同上 |
| 米国の需要増 2025年 | +131 TWh | 同上 |
| インドの需要増 2025年 | +49 TWh | 同上 |
| ロシアの需要 2025年 | −17 TWh(最大の減少) | 同上 |
| 中国の新設容量 2025年 | 太陽光 315 GW、風力 119 GW | 中国 国家能源局 |
| 米国の新設容量 2025年(見込み) | 約 63 GW | 米 EIA |
| 米国の送電網 | 13地域のうち8つが予備率臨界以下 | Goldman Sachs(2025年11月) |
| 世界のデータセンター電力 2025年 | 約 788 TWh(米国 39.7%、中国 26.1%、欧州 18.4%) | Energy Institute |
| 米国のDC電力増 2025年 | +63.5 TWh(需要増の約半分) | 同上 / IEA |

換算: 1 GW × 8,760 h ≒ 8.76 TWh/年。「建てられる量」は需要増(=新たに使える電力)を連続負荷に直した値に、
既存設備の余力(中国の火力利用率低下など)を加味した概算で、チップ供給・冷却水・用地は考慮していません。

## 再生成の方法

```bash
cd ai-power-datacenter
python3 narrate.py     # ナレーション合成 → timeline.json / output/narration.wav / bgm.wav / mix.wav / subtitles_ja.srt
node capture.js        # scene.html を撮影 → output/ai_power_datacenter.mp4(無音)と *_narrated.mp4(mix.wav と合成)、thumbnail.png
./export_upload.sh     # upload/ にアップロード用一式(-14 LUFS 正規化・ステレオAAC・SRT・JPG)
```

- `scene.html` … 7シーンを `setT(t)` で時刻 t 秒の状態に決定論的に描画(ブラウザで開くとプレビュー再生)。タイムラインは `timeline.json` から読む
- `narration.json` … 読み上げ用原稿(数字はかな表記)。`subtitles.json` … 字幕表示用。`narration_script.txt` … 両者の対応表
- `narrate.py` … VOICEVOX CORE(話者: 青山龍星 ノーマル, style 13, 話速 1.15)で合成し、各シーンの尺 = 先頭 0.4 秒 + 音声 + 末尾 0.7 秒 でタイムラインを組む。BGM は `../pacific-war-analysis/bgm.py` を再利用し、発話中は自動で音量を下げてミックス
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し ffmpeg(libx264)にパイプして mp4 化
- 必要なもの: Node.js + `playwright`(Chromium), `ffmpeg`, Python 3 + `numpy` + `voicevox_core`, 日本語フォント(`fonts/` に Noto Sans JP の TTF を置く。無ければ IPAゴシックにフォールバック)

### VOICEVOX のセットアップ(ナレーション用)

VOICEVOX CORE 0.16.0 の GitHub リリースから次を取得し、環境変数でパスを渡します。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| Python ラッパー `voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so.1.17.3`) |
| 音声モデル `15.vvm`(青山龍星) | VOICEVOX/voicevox_vvm releases(タグ 0.16.0) | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 `open_jtalk_dic_utf_8-1.11.tar.gz` | r9y9/open_jtalk releases | `VOICEVOX_DICT`(展開後のディレクトリ) |

スタイルを変える場合は `VOICEVOX_STYLE=81 python3 narrate.py`(81 = 熱血、84 = しっとり)。
VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:青山龍星」のクレジット表記が必要です(動画の最後のカードと `upload/metadata.md` の説明文に記載済み)。

色は単一系列の青 `#3987e5`(ダーク面用に調整済み)、強調は橙 `#d95926`。
