# 旧日本軍のここがすごい(技術編 5選)— ショート動画

縦型ショート動画(1080×1920 / 30fps / 約52秒)。ナレーションは VOICEVOX:四国めたん、BGM は自作(numpy 合成・権利フリー)。

- 完成動画: `output/kyugun_sugoi_short.mp4`
- 字幕: `output/subtitles_ja.srt` / ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`

## 構成

| シーン | 内容 | 主な数値(概数) |
|---|---|---|
| その1 零戦 | 航続距離 | 零戦二一型 約3,350km(増槽付き)/ F4F-4 約1,240km / Bf109E 約660km |
| その2 酸素魚雷 | 射程と航跡 | 九三式 36ノットで約40km / 米Mk15 26.5ノットで約13.7km |
| その3 戦艦大和 | 主砲 | 46cm(アイオワ級 40.6cm、ビスマルク 38cm)/ 九一式徹甲弾 約1,460kg / 射程 約42km |
| その4 空母機動部隊 | 空母の集中運用 | 第一航空艦隊 空母6隻・搭載機 約400機(真珠湾攻撃時) |
| その5 伊400型潜水艦 | 潜水空母 | 全長122m / 晴嵐3機 / 航続距離 約37,500海里(約6万9千km) |
| まとめ | 技術は一流でも、国力と補給の差は埋められなかった | — |

数値は資料・搭載状態によって幅があるため概数です(動画内にも注記)。

## 再生成

```bash
python3 narrate.py   # 四国めたんで音声合成 → output/narration.wav, timeline.json/js, 字幕SRT
node capture.js      # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py       # BGM をダッキングしてミックス、-14 LUFS に正規化 → output/kyugun_sugoi_short.mp4
```

- 原稿は `narrate.py` の `SCRIPT`(読み上げ用テキスト, 字幕用テキスト)。映像の尺は音声の長さから自動で決まる
- 映像は `render.html`(Canvas 2D。ブラウザで開くとプレビュー再生)、BGM は `bgm.py`
- 必要なもの: Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + pyopenjtalk + voicevox_core
  (ONNX Runtime と `0.vvm` の取得方法は `../pacific-war-analysis/README.md` を参照。環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVMS`)

## クレジット

- 音声: **VOICEVOX:四国めたん**(公開時はこのクレジット表記が必要。動画の最後に記載済み)
- フォント: Noto Sans JP / Dela Gothic One(SIL Open Font License、`fonts/` にライセンス同梱)
