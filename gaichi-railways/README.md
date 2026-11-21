# 戦前日本の「外地」の鉄道 — 地図で見るショート動画

戦前の日本で「外地」と呼ばれた地域(台湾・朝鮮・関東州/満鉄・樺太・南洋群島)の鉄道網を、
地図上に路線を描きながら解説する縦型ショート動画(1080×1920 / 30fps / 約60秒)です。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGMは自作。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `metadata.md`)
- 完成動画(ナレーション付き): `output/gaichi_railways_narrated.mp4`
- 完成動画(無音): `output/gaichi_railways.mp4`

## 構成(約60秒)

「東京からヨーロッパまでの通し切符があった」というフックで始め、各地域を1つの要点に絞って紹介し、最後に東京→ヨーロッパの大陸ルートで回収する構成です。

| 時間 | シーン | 要点(画面の大きな一言) |
|---|---|---|
| 0:00–0:05 | フック | 「東京 → ヨーロッパ」の通し切符(イメージ) → 「その道は『外地』の鉄道」 |
| 0:05–0:13 | 外地とは | 台湾・朝鮮・関東州・樺太・南洋群島を順に強調、内地との色分け |
| 0:13–0:20 | 01 台湾 | 内地と同じ 1067mm / 阿里山森林鉄道 762mm |
| 0:20–0:29 | 02 朝鮮 | 内地より広い 1435mm(大陸と直通) / 関釜連絡船から列車は北へ |
| 0:29–0:36 | 03 関東州・満鉄 | 大連〜新京 約700km をあじあ号が 8時間半 |
| 0:36–0:44 | 04 樺太 | 稚泊連絡船 / 1943年 外地 → 内地(島の色が内地色に変わる) |
| 0:44–0:49 | 05 南洋群島 | サトウキビ鉄道 762mm |
| 0:49–0:57 | まとめ | 狭軌と標準軌、東京→下関→釜山→京城→奉天→ハルビン→ヨーロッパ |
| 0:57–1:00 | クレジット | VOICEVOX:四国めたん ほか |

路線の色は軌間で統一しています: 水色 = 1435mm 標準軌 / 黄色 = 1067mm 狭軌 / ピンク破線 = 762mm 軽便 / 白点線 = 連絡船。

## 注意

- 路線は主要駅の座標を結んだ**概略図**です(実際の線形とは異なります)。関東州の境界も概略です。
- 地図の陸地は Natural Earth(現代の国境データ)を使い、外地の範囲は色で示しています。
- 満洲国(1932〜)は形式上は独立国のため外地には含めず、関東州と満鉄附属地を日本の管轄として扱っています(動画内にも注記)。

## 再生成の方法

```bash
cd gaichi-railways
npm i                 # world-atlas / topojson-client(地図データの再生成時のみ必要)
node build_map.js     # map_data.js を生成(コミット済みなので通常は不要)
node capture.js       # output/gaichi_railways.mp4(無音版)
python3 narrate.py    # ナレーション合成 + BGM ミックス → output/gaichi_railways_narrated.mp4
./export_upload.sh    # upload/ に書き出し(-14 LUFS 正規化・ステレオAAC・SRT・JPG)
```

- `render.html` … Canvas 2D の `render(t)` が時刻 t 秒のフレームを決定論的に描画(メルカトル投影、シーンごとにカメラがズーム/パン)。ブラウザで開くとプレビュー再生
- `map_data.js` … Natural Earth 10m から東アジア〜西太平洋を切り出して間引いた陸地データ
- `narrate.py` … VOICEVOX(四国めたん ノーマル, style 2)でシーンごとに合成し、各シーンに収まるよう話速を自動調整。VOICEVOX も Open JTalk 辞書で読むため、誤読する地名(阿里山・大連など)は読み上げ用原稿だけカタカナにしている
- `bgm.py` … `../pacific-war-analysis/bgm.py` と同じ自作BGM合成(numpy のみ、権利フリー)
- 必要なもの: Node.js, `playwright`(Chromium), `ffmpeg`, 日本語フォント(IPAゴシック), Python 3 + `numpy` + `pyopenjtalk`(辞書用) + VOICEVOX CORE

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数(既定値) |
|---|---|---|
| `voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`/home/user/vv/ort/.../libvoicevox_onnxruntime.so`) |
| `0.vvm`(四国めたん・ずんだもん等) | VOICEVOX/voicevox_vvm releases 0.16.0 | `VOICEVOX_VVMS`(`/home/user/vv/vvms`) |

公開時は VOICEVOX の利用規約に従い「VOICEVOX:四国めたん」のクレジットが必要です(動画の最後と説明文に記載済み)。
