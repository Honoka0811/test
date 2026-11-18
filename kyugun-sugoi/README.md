# 旧日本軍 すごい技術ランキング TOP5 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約56秒)。ナレーションは VOICEVOX:青山龍星、BGM・効果音は自作(numpy 合成・権利フリー)。

- 完成動画: `output/kyugun_sugoi_short.mp4`(-14 LUFS 正規化済み・ステレオAAC)
- 字幕: `output/subtitles_ja.srt` / ナレーションのみ: `output/narration.wav` / BGMのみ: `output/bgm.wav`

## 構成と演出

| 時間 | シーン | ねらい |
|---|---|---|
| 0:00 | フック | 「80年前の日本は…」+ 兵器シルエットの高速カット → タイトル → 「1位は最後に発表」で引っぱる |
| 0:08 | 第5位 零戦 | 東京→マニラの航路アニメで 3,000km を実感させる / 米戦闘機の約3倍 |
| 0:16 | 第4位 空母機動部隊 | 空母6隻が並び、350機が発艦 |
| 0:23 | 第3位 伊400型 | 攻撃機3機 / 地球1周半を周回アニメで |
| 0:32 | 第2位 戦艦大和 | 46cm 主砲の口径比較 → 砲撃(画面揺れ)→ 砲弾1発 = 乗用車1台 |
| 0:39 | 第1位 酸素魚雷 | 直前に BGM を止めて溜める / 射程約3倍 / 泡の跡なしで命中 → 「どこから?」 |
| 0:50 | 締め | それでも日本は負けた → 「答えは数字にある」→ 次回(日米戦力差)へ誘導 |

- 「第N位」は画面中央に叩きつけてから上部に移動。上部に 5→1 のカウントダウン表示
- セリフの頭ごとにカメラがズームし、衝撃音(boom / rank / fire / hit)に合わせて画面が揺れてフラッシュ
- 字幕は話す速さに合わせて文字が出て、強調語(`hl`)だけ金色で弾む
- シーン切り替えは赤黒の斜めワイプ + 風切り音

数値はいずれも概数です(動画内にも注記)。零戦 約3,350km(増槽付き)、F4F-4 約1,240km、真珠湾攻撃隊 約350機、伊400型 約37,500海里、九一式徹甲弾 約1,460kg、九三式魚雷 約40km(36ノット)/ Mk15 約13.7km(26.5ノット)。

## 再生成

```bash
python3 narrate.py   # 青山龍星で音声合成 → output/narration.wav, timeline.json/js, 字幕SRT
node capture.js      # render.html を1フレームずつ撮影 → output/video_silent.mp4
python3 mix.py       # BGM(ダッキング)+ 効果音をミックスし -14 LUFS に正規化 → output/kyugun_sugoi_short.mp4
```

- 原稿は `narrate.py` の `SCRIPT`。各行は (読み上げ, 字幕 ※`/`で改行, 強調語, 効果音タグ)。映像・効果音のタイミングは音声の長さから自動で決まる
- 話者を変える: `VOICEVOX_STYLE=2 python3 narrate.py`(2 = 四国めたん。`0.vvm` が必要)
- 映像は `render.html`(Canvas 2D。ブラウザで開くとプレビュー再生)、BGM は `bgm.py`、効果音は `mix.py`
- 必要なもの: Node.js + playwright(Chromium)、ffmpeg、Python 3 + numpy + pyopenjtalk + voicevox_core、音声モデル `15.vvm`
  (ONNX Runtime と vvm の取得方法は `../pacific-war-analysis/README.md` を参照。環境変数 `VOICEVOX_ORT` / `VOICEVOX_VVMS`)

## クレジット

- 音声: **VOICEVOX:青山龍星**(公開時はこのクレジット表記が必要。動画の最後に記載済み)
- フォント: Noto Sans JP / Dela Gothic One(SIL Open Font License、`fonts/` にライセンス同梱)
