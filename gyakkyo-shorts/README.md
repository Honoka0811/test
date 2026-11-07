# 逆境 ── 折れる人と強くなる人の差は、たった一つ(YouTube ショート)

テーマ「逆境」のモチベーション系ショート動画(1080×1920 / 30fps / 約59秒)。
ナレーションは **VOICEVOX:四国めたん**、BGM と効果音はプログラム合成(権利フリー)。
字幕は VOICEVOX のモーラ長から算出した発話タイミングに同期し、発話中のフレーズが黄色くポップする。

- **アップロード用一式: `upload/`**(最終 mp4・字幕 SRT・サムネイル JPG・タイトル/説明文/タグ/チェックリストの `metadata.md`)
- 台本: `script.txt`
- ナレーション音声のみ: `output/narration.wav` / BGM のみ: `output/bgm.wav`
- 字幕タイミング: `output/timeline.json`

## 構成と演出(約59秒)

| 時間 | シーン | 演出 |
|---|---|---|
| 0:00–0:05 | フック | 白フラッシュ→巨大な赤「逆境」(心拍で明滅)→左右分割「折れる/強くなる」→巨大な「1」が衝撃波と画面揺れで出現 |
| 0:05–0:14 | 共感 | 雨・稲光・ゆっくりズーム、「なんで自分だけ」が傾いて大きく出る |
| 0:14–0:24 | 転換:竹 | 地下で根が伸びる(年カウンタ 1→5年目)→竹が 0.5 秒で画面上端まで急成長、スピード線・画面揺れ・「+100cm」 |
| 0:24–0:32 | 事例 | 原稿に「不採用」スタンプ 12 連打(効果音同期)→黄金の光と「シリーズ累計 5億部超」 |
| 0:32–0:45 | 核心 | 残り火パーティクル、「終わり」に赤い×、「根を張る時間」が金色に輝き根が光る(BGM 最高潮) |
| 0:45–0:50 | 締め | 夜明け、竹林シルエット、昇る太陽、新芽 |
| 0:50–0:59 | CTA | コメント欄モックに「根を張る」がタイピング、「1年後、ここに報告しに来て」、保存誘導、クレジット |

共通: 上部プログレスバー、フィルムグレイン、ビネット、シーン切り替えのディップ/フラッシュ。最後は暗転してループ時に冒頭のフラッシュへ自然につながる。

## 音
- `bgm.py` … Aマイナー / 96BPM。心拍+サブドローン(フック)→雨のノイズ床+まばらなピアノ(共感)→ストリングスのクレッシェンド+スネアロール+ライザー(ビルド)→発芽でドロップ(キック/クラップ/ベース/ピアノ/ストリングス)→「根を張る時間」でクラッシュ→ドラム抜きの温かいコード(締め)→軽いプラック(CTA)。
  効果音(インパクト、スタンプ、雷鳴、シマー、タイピング音)も `timeline.json` の発話時刻に同期して生成。
- `mix.py` … ナレーションの包絡で BGM を自動ダッキング(発話時 約 -8dB)し、SFX と合わせてソフトリミッタ後に動画へ合成。
- `export_upload.sh` … -14 LUFS(YouTube 基準)に線形正規化してステレオ AAC で書き出し。

## 再生成の方法

```bash
cd gyakkyo-shorts
python3 narrate.py          # VOICEVOX でナレーション合成 → output/narration.wav, timeline.json/js, subtitles_ja.srt
node capture.js             # render.html を 1 フレームずつ撮影 → output/video_silent.mp4(約 10 分)
python3 mix.py              # BGM/SFX 生成 + ダッキングミックス → output/gyakkyo_shorts.mp4
node capture.js --thumb     # サムネイル → output/thumbnail.png
./export_upload.sh          # upload/ にアップロード用一式を書き出す
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)。`output/timeline.js` を読んで字幕と演出のタイミングを決める
- `capture.js` … Playwright(Chromium)で撮影し ffmpeg(libx264)へパイプ。`--frames 1.0,2.5` で指定時刻の静止画、`--thumb` でサムネイル
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `scipy` + `pyopenjtalk`、VOICEVOX CORE(下記)

### VOICEVOX のセットアップ(ナレーション用)

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん・ずんだもん ほか) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 同梱のものを自動使用 | `VOICEVOX_DICT`(任意) |

スタイルを変える場合は `VOICEVOX_STYLE=6 python3 narrate.py`(0 あまあま / 2 ノーマル / 4 セクシー / 6 ツンツン)。話速は `VOICEVOX_SPEED`(既定 1.18)。
台本は `narrate.py` の `SCRIPT`(シーン→行→パート)。パートの区切りが字幕の強調単位になる。
VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要(動画末尾と `upload/metadata.md` の説明文に記載済み)。

## ライセンス
- フォント `fonts/`: Zen Kaku Gothic New / M PLUS 1p(SIL Open Font License 1.1、同梱の OFL-*.txt)
- BGM・効果音・映像: 本リポジトリで生成した自作物
