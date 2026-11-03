# 40代のうちにやっておくべきこと10選 — ショート動画

イラストと絵文字を多めに使い、テンポよく10項目を紹介する縦型ショート動画(1080×1920 / 30fps / 約70秒)です。
ナレーションは VOICEVOX の **四国めたん**、BGM はパッヘルベル「カノン」のポップ・アレンジ(自作)です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・`metadata.md` に手順とタイトル/説明文/タグ・`youtube_metadata.json` + `upload_youtube.py` で API アップロードも可)
- 完成動画: `output/forties_checklist_narrated.mp4`
- 無音版(映像のみ): `output/forties_checklist.mp4`
- ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`
- ナレーション原稿: `narration_script.txt`

## 構成(約70秒)

| 時間 | シーン | 画面 |
|---|---|---|
| 0:00–0:03 | タイトル | 「40代のうちに やっておくべきこと 10選」+ 紙吹雪・クラッカー |
| 0:03–0:09 | ① 毎年の健康診断 | 診察のイラスト + 聴診器・病院・チェック |
| 0:09–0:16 | ② 運動を習慣にする | ランニングのイラスト + 力こぶ・シューズ・炎 |
| 0:16–0:22 | ③ 歯のメンテナンス | 大きな歯の3D絵文字 + 歯ブラシ・カレンダー |
| 0:22–0:28 | ④ 睡眠と食事の見直し | 食卓のイラスト + ベッド・zzz・サラダ・月 |
| 0:28–0:34 | ⑤ 老後資金の計画 | 貯金箱のイラスト + お金袋・チャート・コイン・銀行 |
| 0:34–0:41 | ⑥ 学び直し | 卒業帽のイラスト + 本・ノートPC・電球 |
| 0:41–0:46 | ⑦ 親と話しておく | 祖母と孫のイラスト + おじいさん・おばあさん・家・ハート |
| 0:46–0:52 | ⑧ 人間関係の整理 | 友人とコーヒーのイラスト + ハグ・握手・ハート |
| 0:52–0:58 | ⑨ やりたかったことに挑戦 | 旅のイラスト + 飛行機・ギター・カメラ・山 |
| 0:58–1:03 | ⑩ 持ち物と保険の見直し | 片付けのイラスト + 段ボール・ほうき・盾・レシート |
| 1:03–1:10 | まとめ | 10項目のチェックリストが順にチェック →「まずは1つ、今日から。」+ クレジット |

各項目は「番号バッジが弾む → タイトルがスライドイン → イラストカードがポップ → 絵文字が順に飛び出す → 字幕」
の順に 1 秒以内で出そろい、シーン間は円形ワイプで切り替わります。シーンの尺はナレーションの長さから自動で決まります。

## 再生成の方法

```bash
cd forties-checklist
python3 tools/build_assets.py   # assets/assets.js(イラスト・絵文字の埋め込み)を再生成する場合のみ
python3 narrate.py              # ナレーション合成 → output/narration.wav, timing.json, subtitles_ja.srt
node capture.js                 # 映像を撮影 → output/forties_checklist.mp4(無音)
python3 mix.py                  # BGM 合成 + ダッキング + 効果音ミックス → output/forties_checklist_narrated.mp4
./export_upload.sh              # upload/ にアップロード用一式(-14 LUFS 正規化・SRT・サムネイル)
```

| ファイル | 役割 |
|---|---|
| `render.html` | Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)。項目の文言・色・絵文字は先頭の `ITEMS` で変更 |
| `capture.js` | Playwright(Chromium)で 1 フレームずつ撮影し ffmpeg(libx264)で mp4 化。`PREVIEW_TIMES="3,10" node capture.js` で静止画だけ確認できる |
| `narrate.py` | 原稿 `SCRIPT` を VOICEVOX(四国めたん ノーマル, style 2)で合成。句読点の間を詰め、話速 1.25 でテンポよく。各シーンの尺を `output/timing.json` に書き出す |
| `bgm.py` | パッヘルベル「カノン」(ニ長調・100BPM)のアレンジを GM 音源(GeneralUser GS)で演奏。ピアノのアルペジオ + ピチカート + ストリングス + フルート/グロッケンの変奏 + 軽いドラム + 簡易リバーブ |
| `mix.py` | ナレーション中は BGM を自動で下げ(ダッキング)、シーン切替のポップ音やチェック音(numpy で合成)を重ねて動画に合成 |
| `tools/build_assets.py` | unDraw と Fluent Emoji の SVG を選んで `assets/` にコピーし、Canvas から読める `assets/assets.js` を生成 |

### 必要なもの

- Node.js + `playwright`(Chromium)、`ffmpeg`
- Python 3 + `numpy`、`voicevox_core`(0.17 系)+ `pyopenjtalk`(辞書用)、`tinysoundfont`(BGM 用、`pip install --no-deps tinysoundfont`)
- 日本語フォント: Rounded M+ 1c(`MPLUSRounded1c-*.ttf`)を `~/.fonts` に。無い場合は Zen Maru Gothic → Noto Sans JP → システムフォントの順にフォールバック
- SoundFont: [GeneralUser GS](https://github.com/mrbumpy409/GeneralUser-GS)(`GeneralUser-GS.sf2`)。環境変数 `SF2` でパスを指定(既定 `/home/user/assets/sf2/GeneralUser-GS.sf2`)

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| Python ラッパー `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん・ずんだもん等) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 同梱のものを自動使用 | `VOICEVOX_DICT`(任意) |

話し方を変える場合は `VOICEVOX_STYLE=0 python3 narrate.py`(0 = あまあま, 6 = ツンツン, 4 = セクシー)、
話速は `NARR_SPEED=1.2`、句読点の間は `NARR_PAUSE=0.8` のように指定します。

## 素材とクレジット

| 素材 | ライセンス | 表記 |
|---|---|---|
| ナレーション: VOICEVOX 四国めたん | VOICEVOX 利用規約(商用・非商用可、クレジット必須) | 「VOICEVOX:四国めたん」を動画末尾と説明文に記載 |
| イラスト: [unDraw](https://undraw.co)(Katerina Limpitsouni) | unDraw License(商用可・表記不要) | 任意で記載 |
| 絵文字: [Fluent Emoji](https://github.com/microsoft/fluentui-emoji)(Microsoft) | MIT License | 説明文に記載 |
| BGM: パッヘルベル「カノン」 | 原曲はパブリックドメイン。演奏データは自作、音源は GeneralUser GS(自由に利用可) | 権利表記不要 |
| 効果音 | numpy で合成(自作) | 不要 |
| フォント: Rounded M+ 1c | M+ FONTS LICENSE(自由に利用可) | 不要 |

この環境からは写真素材サイト(Unsplash/Pexels/Wikimedia 等)に接続できなかったため、写真の代わりに
イラストと3D絵文字で画面を構成しています。写真を使いたい場合は `render.html` の `drawImg(IMG.undraw[sc.id], …)` の部分を
差し替えれば、同じ位置に写真を入れられます。
