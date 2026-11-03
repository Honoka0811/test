# 30代のうちにやっておくべきこと10選 — ショート動画

縦型（1080×1920 / 30fps / 約74秒）のショート動画です。
ナレーションは VOICEVOX の四国めたん、BGM はパッヘルベルの「カノン」をポップ調にアレンジしたものです。

- 完成動画: `30dai_yarubeki_10sen.mp4`
- 台本・字幕タイミング: `script/narration.md`, `script/narration_timing.json`
- BGM: `script/bgm_canon_pop.mp3`（MIDI: `script/bgm_canon_pop.mid`）

## 構成

| # | タイトル | 主なビジュアル |
|---|---|---|
| intro | 30代のうちにやっておくべきこと 10選 | お祝いのイラスト＋クラッカー・星 |
| 01 | 健康に投資する | 筋トレ／ジョギング |
| 02 | お金を仕組み化する | 家計・資産グラフ |
| 03 | 自分の武器を磨く | 集中・自信 |
| 04 | 人間関係を整える | 友情・ハイタッチ |
| 05 | 親と旅行に行く | 旅行・思い出 |
| 06 | 大きく挑戦する | ロケット・ヒーロー |
| 07 | 住環境を整える | くつろぎの部屋・家 |
| 08 | 学び直しをする | 勉強・読書 |
| 09 | 一生モノの趣味 | 音楽・キャンプ |
| 10 | 今を記録に残す | 写真・思い出 |
| outro | 全部やらなくてOK | 「保存して、あとで見返そう」 |

各シーンは「番号バッジ → タイトル → イラストカード → 絵文字がポップイン → 中盤でイラスト切替」の流れで、
シーン間はアクセントカラーのワイプで切り替わります。字幕は VOICEVOX の音素長から句読点ごとに同期しています。

## 作り直し方

```bash
# 前提: ffmpeg, fluidsynth(+FluidR3_GM.sf2), rsvg-convert, Python3 (Pillow, numpy, mido)
# VOICEVOX CORE 0.15.7 (Python wheel + onnxruntime 1.13.1 + Open JTalk 辞書) を別 venv に入れておく

# 1. ナレーション合成（四国めたん / speaker id 2）
LD_LIBRARY_PATH=<onnxruntime/lib> <venv>/bin/python tools/gen_voice.py <scratch> <download-dir>

# 2. BGM（カノン・ポップアレンジ）を MIDI → WAV
python3 tools/gen_bgm.py bgm/canon_pop.mid
fluidsynth -ni -r 48000 -g 0.7 -F bgm/canon_pop_raw.wav /usr/share/sounds/sf2/FluidR3_GM.sf2 bgm/canon_pop.mid
ffmpeg -i bgm/canon_pop_raw.wav -af "loudnorm=I=-18:TP=-2:LRA=9,highpass=f=40" bgm/canon_pop.wav

# 3. 映像フレームを合成（PIL → ffmpeg パイプ）
SCRATCH=<scratch> python3 tools/build_video.py render out/video_silent.mp4

# 4. ナレーション（-16 LUFS）＋ BGM（サイドチェインでダッキング）をミックスして結合
#    詳細は tools/build_video.py のタイムラインと README 下部のコマンドを参照
```

素材は `tools/undraw2svg.py` で unDraw の React コンポーネントを SVG に戻し、`rsvg-convert` で PNG 化しています。

## 素材とクレジット

- ナレーション: **VOICEVOX：四国めたん**（動画内にもクレジット表記あり）
- イラスト: [unDraw](https://undraw.co)（MIT License）
- 絵文字: [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji)（MIT License）
- フォント: Zen Maru Gothic / M PLUS Rounded 1c / Dela Gothic One（SIL Open Font License）
- BGM: J. パッヘルベル「カノン ニ長調」（パブリックドメイン）のオリジナルアレンジ。音源は FluidR3_GM サウンドフォント（MIT License）
- 写真素材サイト（Unsplash / Pexels / Pixabay 等）はこの制作環境からアクセスできなかったため、実写写真は使わず、イラストと立体絵文字で構成しています。
