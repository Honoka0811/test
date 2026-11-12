# 地図で見る 戦前「外地」の日本企業工場 — ショート動画

戦前の朝鮮・満洲・台湾・樺太にあった日本の大企業の工場を、地図を動かしながら紹介する縦型ショート動画
(1080×1920 / 30fps / 約73秒)です。ナレーションは VOICEVOX:四国めたん、BGM は自作(プログラム合成)。

- **完成動画: `output/gaichi_factories_short.mp4`**(H.264 + AAC ステレオ、-14 LUFS)
- 字幕: `output/subtitles_ja.srt` / ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`

## 構成

| 時間 | 地域 | 紹介する工場 |
|---|---|---|
| 0:00 | イントロ | 広域図で朝鮮・満洲・台湾・樺太を順に点灯 |
| 0:10 | 朝鮮 | 興南(日本窒素肥料)、水豊ダム、兼二浦・清津(日本製鉄)、京城(鐘淵紡績など) |
| 0:28 | 満洲 | 鞍山(満鉄 → 昭和製鋼所)、撫順炭鉱、新京(満洲重工業開発) |
| 0:42 | 台湾 | 虎尾(大日本製糖)、総爺(明治製糖)、橋仔頭(台湾製糖)、高雄(日本アルミニウム・浅野セメント)、日月潭 |
| 0:54 | 樺太 | 王子製紙の9工場(豊原・真岡・恵須取ほか) |
| 1:02 | まとめ | 1945年 敗戦、在外資産の喪失 |

## 地図についての注意

- 国境・海岸線は Natural Earth の現在のデータです。
- 当時の領域は近似です: 朝鮮 = 現在の韓国+北朝鮮、樺太 = サハリン島の北緯50度以南、
  満洲 = 黒竜江・吉林・遼寧の3省+内モンゴル東部(概略。熱河省などは含めていません)。
- 工場の位置は都市の位置に置いた目安です。

## 再生成の方法

```bash
./setup.sh                  # VOICEVOX CORE・フォント・Natural Earth を取得(初回のみ)
python3 build_map.py vendor/ne/c/ne_10m_admin_0_countries.shp vendor/ne/p/ne_10m_admin_1_states_provinces.shp
python3 narrate.py          # ナレーション合成 → output/narration.wav, data/timeline.js, 字幕SRT
node capture.js             # 全フレームを撮影 → output/video_silent.mp4
python3 mix.py              # BGM を合成してミックス → output/gaichi_factories_short.mp4
```

- `narrate.py` … 原稿(`LINES`)を1文ずつ合成。映像の時刻はすべてここで作る `data/timeline.js` に追従するので、原稿を変えたら上の3コマンドを順に再実行するだけです。読みを誤る地名は読み上げ用テキストだけカタカナにしています。
- `render.html` … Canvas 2D で `render(t)` が時刻 t のフレームを描画。ブラウザで開くとプレビュー再生(`?t=30` で途中から)。工場の位置とラベルは `MARKERS`。
- `capture.js` … Playwright で1フレームずつ撮影して ffmpeg に渡す。`node capture.js --stills 12,30` で静止画確認。
- `bgm.py` … 84BPM のローファイ風 BGM を numpy だけで合成(外部音源なし)。
- `mix.py` … ナレーション中だけ BGM を下げてミックスし、-14 LUFS に正規化。

## クレジット・ライセンス

- 音声: **VOICEVOX:四国めたん**(公開時はこのクレジット表記が必要です。動画の最後に表示済み)
- 地図: Natural Earth(パブリックドメイン) / フォント: Noto Sans JP(SIL OFL)
