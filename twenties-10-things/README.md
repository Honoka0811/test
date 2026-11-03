# 20代のうちにやっておくべきこと10選 — ショート動画

縦型 1080×1920 / 30fps / 66.5 秒のショート動画です。イラスト多めのフラットデザインで、
ナレーションは VOICEVOX の **四国めたん**、BGM は J.S.バッハ「プレリュード ハ長調」(平均律クラヴィーア曲集 第1巻 第1番)を軽いポップ調に自作アレンジしたものです。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `metadata.md`)
- 完成動画(ナレーション+BGM): `output/twenties_10_narrated.mp4`
- 無音版(映像のみ): `output/twenties_10.mp4`
- ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`(自作・権利フリー)

## 構成(66.5秒)

| 時間 | シーン | イラスト |
|---|---|---|
| 0:00–0:05 | タイトル「20代のうちにやっておくべきこと 10選」 | 紙吹雪 + ミニアイコン |
| 0:05–0:10 | ① 海外に行く | 地球儀・飛行機・スーツケース・チケット |
| 0:10–0:16 | ② 本を読む習慣 | 積んだ本・開いた本・電球・カップ |
| 0:16–0:22 | ③ お金の勉強 | 貯金箱・落ちるコイン・右肩上がりのグラフ |
| 0:22–0:27 | ④ 体を鍛える | ランナー・ダンベル・ハート(心拍) |
| 0:27–0:33 | ⑤ 失敗を恐れず挑戦する | 夜空・ロケット発射・山頂の旗 |
| 0:33–0:38 | ⑥ スキルを身につける | ノートPC(コード)・吹き出し・学位帽 |
| 0:38–0:44 | ⑦ 人とのつながりを広げる | 5人のアバターとつながる線 |
| 0:44–0:50 | ⑧ 一人暮らしをする | 家・観葉植物・鍵 |
| 0:50–0:55 | ⑨ 家族との時間 | 親子・ハート・プレゼント |
| 0:55–1:01 | ⑩ 自分の「好き」を見つける | パレット・カメラ・音符 |
| 1:01–1:06 | まとめ + クレジット | 10個のミニアイコン |

各シーンはサークルワイプで切り替わり、番号バッジ → タイトル → イラスト(ポップイン)→ キャプションカードの順にテンポよく出ます。

## 再生成の方法

```bash
cd twenties-10-things
node capture.js                 # output/twenties_10.mp4(無音版)を生成
python3 narrate.py              # ナレーション合成 + BGM ミックス → output/twenties_10_narrated.mp4
node capture.js --thumb 2.6     # サムネイル output/thumbnail.png
./export_upload.sh              # upload/ にアップロード用一式(-14 LUFS 正規化)
node capture.js --frames 7,30   # 指定秒のフレームを PNG で確認
python3 bgm.py 66.5 bgm.wav     # BGM だけ書き出す
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画。ブラウザで開くとプレビュー再生。イラストはすべて Canvas のパスで描いた自作(外部画像なし)
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し ffmpeg(libx264)へパイプ
- `bgm.py` … バッハ「プレリュード ハ長調」のポップアレンジ(92BPM)。原曲の分散和音をピアノで弾き、パッド・ベース・軽いドラム・ベルを重ねて numpy だけで合成。全パートが各小節の和音構成音だけを使うので不協和音が出ない(減七の和音が出る小節は省略)
- `narrate.py` … 原稿を VOICEVOX(四国めたん ノーマル, style 2)で合成し、各シーンの尺に収まるよう話速を自動調整。BGM はナレーション中に自動で音量を下げてミックス(ダッキング)
- 必要なもの: Node.js + `playwright`(Chromium), `ffmpeg`, Python 3 + `numpy` + `pyopenjtalk`, `fonts/`(M PLUS Rounded 1c, SIL OFL)

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん/ずんだもん ほか) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 同梱のものを自動使用 | `VOICEVOX_DICT`(任意) |

スタイルを変える場合は `VOICEVOX_STYLE=0 python3 narrate.py`(0=あまあま, 6=ツンツン, 4=セクシー)。
VOICEVOX の音声を公開する場合は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画の最後と `upload/metadata.md` に記載済み)。

原稿は `narrate.py` の `LINES`、画面のタイトル/キャプション/イラストは `render.html` の `ITEMS` にあります。
