# 複利のチカラ — 投資ショート動画(月3万円×30年で2,500万円?)

YouTube ショート向けの縦型動画(1080×1920 / 30fps / 57.5秒)。「月3万円を30年積み立てたらいくら?」というフックから、
複利の加速・始めるタイミングの差・72の法則までを、数字の演出(スロット、カウントアップ、爆発リビール、複利カーブ、スタンプ)で見せます。
ナレーションは VOICEVOX:四国めたん、BGM・効果音は numpy で合成した自作(権利フリー)です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/投稿メモの `metadata.md`)
- 完成動画: `output/compound_shorts.mp4`(ナレーション+BGM+効果音、字幕焼き込み)
- サムネイル: `output/thumbnail.png`(本編とは別に作った専用デザイン)
- 無音版: `output/video_silent.mp4` / ナレーション: `output/narration.wav` / BGM: `output/bgm.wav` / 効果音: `output/sfx.wav`
- 原稿: `narration_script.txt`

## 構成(57.5秒)

| 時間 | シーン | 演出 |
|---|---|---|
| 0:00–0:05 | フック | 「月3万円」スラム → 「30年」 → スロット回転「?,???万円」→ 溜め |
| 0:05–0:11 | 貯金だけなら | 棒グラフが 1,080万 までカウントアップ → 「年利5%」バッジ → チャージ+ライザー |
| 0:11–0:18 | リビール | 2,497万 へ爆発(フラッシュ・揺れ・コイン噴出)→ 「+1,417万円 複利が増やした分」 |
| 0:18–0:30 | 複利カーブ | 曲線が伸びながら 10年/20年/30年 のマーカーがポップ → 「後半ほど一気に加速!」 |
| 0:30–0:39 | 10年遅れると | 今すぐ 2,497万 vs 10年後に開始 1,233万 → 「半分以下」スタンプ |
| 0:39–0:50 | 72の法則 | 「? ÷ 年利」→「72 ÷ 年利」ドン → 5%=約14年 / 7%=約10年、コインが2枚に |
| 0:50–0:57 | まとめ/CTA | 砂時計「時間は誰にも増やせない」→「保存して、始める日を決めよう」+ 免責・クレジット |

## 使用した数値

月3万円・年利5%(月複利)・税金/手数料なしの試算。`FV = 3万 × ((1+r)^n − 1) / r`(r = 0.05/12)。

| 経過 | 元本 | 評価額 |
|---|---|---|
| 10年 | 360万 | 約466万 |
| 20年 | 720万 | 約1,233万 |
| 30年 | 1,080万 | 約2,497万 |

72の法則: 2倍になる年数 ≈ 72 ÷ 年利(%)。5% → 14.4年、7% → 10.3年。

## 再生成の方法

```bash
cd investment-compound-shorts
python3 narrate.py          # VOICEVOX でナレーション合成 → output/narration.wav, captions.json, subtitles_ja.srt
node capture.js             # render.html を 1 フレームずつ撮影 → output/video_silent.mp4(字幕焼き込み)
python3 mix.py              # BGM(bgm.py)+効果音+ナレーションをミックス → output/compound_shorts.mp4
./export_upload.sh          # upload/ に -14 LUFS 正規化した最終版・SRT・サムネイルを書き出す
node capture.js --thumb             # サムネイル専用フレーム → output/thumbnail.png
node capture.js --stills 2.5,13 dir   # 確認用の静止画
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)。字幕は `output/captions.json` を読み込む
- `capture.js` … Playwright(Chromium)で撮影し ffmpeg(libx264)にパイプ
- `narrate.py` … 四国めたん(style 2)で合成。各シーン尺に収まるよう話速を自動調整(1.12〜1.25)。字幕チャンクのタイミングも書き出す
- `bgm.py` … 128BPM / Aマイナー。サイドチェインベース・4つ打ち・クラップ・ハット・コードスタブ・16分アルペジオ・ライザー・インパクト。シーンに合わせて intro/build/drop/break/outro を切替
- `mix.py` … 効果音(ウーシュ、スラム、ポップ、コイン、ディング、スロットのチック、溜めのスティング)を合成し、ナレーション中は BGM を自動で下げて(ダッキング)ミックス
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `scipy` + `voicevox_core` + `pyopenjtalk`(辞書用)
- フォント: Dela Gothic One / Zen Kaku Gothic New / M PLUS 1p(いずれも SIL OFL。`fonts/` に同梱)

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(展開後の `lib/libvoicevox_onnxruntime.so`) |
| `0.vvm`(四国めたん・ずんだもん等) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 | `pyopenjtalk` 同梱(初回に自動DL) | `VOICEVOX_DICT`(任意) |

スタイルを変える場合は `VOICEVOX_STYLE=6 python3 narrate.py`(0=あまあま, 2=ノーマル, 4=セクシー, 6=ツンツン)。
VOICEVOX の音声を公開する場合は、利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画末尾のカードと `upload/metadata.md` の説明文に記載済み)。

## 免責

本動画は一般的な情報提供を目的としたもので、特定の金融商品の勧誘・推奨ではありません。試算値は前提条件(年利5%・月複利・税金/手数料なし)に基づく仮定であり、将来の成果を保証しません。
