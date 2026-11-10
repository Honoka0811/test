# 世界を変えた物理学の大発見 5選 — ショート動画

物理学の5つの大発見と、それが今の暮らしをどう変えたかを紹介する縦型ショート動画です(1080×1920 / 30fps / 約74秒)。
ナレーションは VOICEVOX の四国めたん(ノーマル)、BGM は numpy で合成したオリジナル曲です。字幕は映像に焼き込み済みで、SRT も別に用意しています。

- **完成動画: `output/physics_discoveries.mp4`**(-14 LUFS に正規化、ステレオAAC)
- サムネイル: `output/thumbnail.jpg`
- 字幕: `output/subtitles_ja.srt`
- ナレーションのみ: `output/narration.wav` / BGM のみ: `output/bgm.wav`

## 構成

| 時間 | シーン | 内容 | 映像 |
|---|---|---|---|
| 0:00–0:08 | タイトル | 世界を変えた物理学の大発見 5選 | 回転する原子のロゴ |
| 0:08–0:21 | ① 万有引力(ニュートン, 1687年) | リンゴも月も同じ法則 → 人工衛星・ロケット | 落ちるリンゴと地球を回る月 |
| 0:21–0:31 | ② 電磁誘導(ファラデー, 1831年) | 磁石を動かすと電気が流れる → 発電機・モーター | 磁石の往復でコイルに電流、電球が点灯 |
| 0:31–0:42 | ③ 電磁波(マクスウェル, 1864年 予言 / 1888年 ヘルツが実証) | 光の速さで伝わる波 → ラジオ・スマホ・Wi-Fi | 電場Eと磁場Bの波が進む |
| 0:42–0:54 | ④ 相対性理論(アインシュタイン, 1905・1915年) | 時間と空間は伸び縮みする → GPS の補正 | 重力でゆがむ時空と、地上・衛星の時計 |
| 0:54–1:05 | ⑤ 量子力学(プランク、ボーアほか, 1900〜1920年代) | 電子は粒であり波でもある → 半導体・コンピューター | 二重スリット実験で干渉縞が浮かぶ |
| 1:05–1:14 | まとめ | 5つの発見の一覧、「次の大発見は、あなたかも。」、クレジット | |

GPS の数値は、衛星の時計が地上より1日あたり約38マイクロ秒進み(特殊相対論で約−7μs、一般相対論で約+45μs)、
補正しないと位置が1日に約10km以上ずれる、という一般的な説明に基づいています。

## 再生成の方法

```bash
cd physics-discoveries
./make.sh
```

`make.sh` は次の4つを順に実行します。

1. `voice.py` … 原稿を文ごとに VOICEVOX(四国めたん ノーマル, style 2)で合成。**実際の音声長からシーン尺と字幕タイミングを決め**、`output/narration.wav`・`output/timings.json`・`output/timings.js`・`output/subtitles_ja.srt` を書き出す。原稿は `SCRIPT` にあり、書き換えて再実行すれば動画の尺も自動で追従します(字幕の `|` は改行位置の指定)
2. `capture.js` … `render.html`(Canvas 2D、`render(t)` が時刻 t のフレームを描画)を Playwright で1フレームずつ撮影し、ffmpeg で `output/video_silent.mp4` に変換。`render.html` はブラウザで直接開くとプレビュー再生できます
3. `mix.py` … `bgm.py` の BGM をナレーション中だけ自動で下げて(ダッキング)ミックスし、映像と合成して -14 LUFS に正規化
4. `bgm.py` … BGM 単体を `output/bgm.wav` に書き出し(Cメジャー・100BPM。パッド + FMベルのアルペジオ + ベース + 軽いキック/ハイハット。外部音源を使わないため権利表記不要)

必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、IPAゴシック・DejaVu フォント、Python 3 + `numpy` + `pyopenjtalk` + `voicevox_core`

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 環境変数(既定値) |
|---|---|---|
| `voicevox_core-0.16.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`/home/user/vv/ort/.../libvoicevox_onnxruntime.so`) |
| 音声モデル `0.vvm`(四国めたん・ずんだもん ほか) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(`/home/user/vv/vvms`) |
| Open JTalk 辞書 | `pyopenjtalk` が初回実行時に自動取得 | `VOICEVOX_DICT`(任意) |

スタイルを変える場合は `VOICEVOX_STYLE=0 ./make.sh`(0 = 四国めたん あまあま、6 = ツンツン、3 = ずんだもん)のようにします。

## クレジット

VOICEVOX の利用規約により、公開時は **「VOICEVOX:四国めたん」** の表記が必要です(動画の最後と、下の説明文に記載済み)。

### 投稿用テキスト例

- タイトル: `世界を変えた物理学の大発見5選 #shorts`
- 説明文:
  ```
  ニュートンの万有引力から量子力学まで、私たちの暮らしを変えた物理学の大発見を5つ紹介します。
  ナレーション:VOICEVOX:四国めたん
  BGM:オリジナル
  #物理 #科学 #雑学 #shorts
  ```
