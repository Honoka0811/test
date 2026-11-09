# フレネミーとは? — ショート動画

「友達のふりをした敵=フレネミー」の特徴と対処法を紹介する縦型ショート動画です
(1080×1920 / 30fps / 約69秒 / H.264 + AAC ステレオ / -14 LUFS)。

- **完成動画: `output/frenemy_narrated.mp4`**(ナレーション + BGM + 焼き込み字幕)
- ナレーション: **VOICEVOX:四国めたん**(ノーマル)
- BGM: `bgm.py` で numpy だけで合成した自作曲(外部音源不使用・権利フリー)
- 字幕ファイル: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg`
- 音声のみ: `output/narration.wav`(ナレーション)、`output/bgm.wav`(BGM)

## 構成

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00 | タイトル | 「その友達、本当に味方?」笑顔の仮面が割れて本性が見える |
| 0:05 | 定義 | Friend(友達)+ Enemy(敵)= Frenemy |
| 0:13 | 特徴① | 褒めながら落とす(「かわいい!」「安かったでしょ?笑」のチャット) |
| 0:23 | 特徴② | 成功を素直に喜ばない(「運が良かっただけでしょ」) |
| 0:31 | 特徴③ | 打ち明けた秘密が広まる(出どころはその人) |
| 0:38 | 特徴④ | 告げ口で人間関係を引き裂く |
| 0:46 | サイン | 会ったあと疲れる/自信がなくなる/本音を話せない →「要注意」 |
| 0:53 | 対処法 | 距離を置く・大切な情報は話さない・挑発に反応しない |
| 1:01 | まとめ | 「心が軽くなる人を、大切に。」+ クレジット |

## 投稿用

**タイトル案**
1. その友達、本当に味方?「フレネミー」の特徴4つと対処法 #Shorts
2. 褒めながら落としてくる友達、それフレネミーかも #Shorts

**説明文**
```
友達のふりをして、裏で足を引っ張る「フレネミー」。
よくある特徴4つと、上手な付き合い方・距離の取り方をまとめました。

ナレーション: VOICEVOX:四国めたん
BGM: 自作
```

**タグ**: `#フレネミー #人間関係 #友達 #心理学 #職場の人間関係 #Shorts`

VOICEVOX の音声を公開する際は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画の最後と説明文に記載済み)。

## 再生成

```bash
cd frenemy
./make.sh
```

1. `narrate.py` … 原稿(`SCRIPT`)を文単位で VOICEVOX 合成。実測した発話長からシーン尺と字幕タイミングを決め、`timeline.js` と SRT を出力
2. `capture.js` … `render.html`(Canvas 2D、`render(t)` が時刻 t のフレームを決定論的に描画)を Playwright で 1 フレームずつ撮影し ffmpeg で mp4 化
3. `mix.py` … `bgm.py` の BGM をナレーション中は自動で下げて(ダッキング)ミックスし、-14 LUFS に揃えて映像と合成

原稿を書き換えて `./make.sh` を実行すれば、尺・字幕も自動で追従します。`render.html` はブラウザで開くとプレビュー再生できます。

### VOICEVOX のセットアップ

`/home/user/vv`(環境変数 `VOICEVOX_HOME` で変更可)に次を置きます。

| 必要なもの | 取得元 |
|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` |
| `ort/voicevox_onnxruntime-linux-x64-1.17.3/` | VOICEVOX/onnxruntime-builder releases |
| `vvms/0.vvm`(四国めたん・ずんだもん 等) | VOICEVOX/voicevox_vvm releases |
| `open_jtalk_dic_utf_8-1.11/` | r9y9/open_jtalk releases |

スタイルを変える場合は `VOICEVOX_STYLE=0 ./make.sh`(0 = 四国めたん あまあま、6 = ツンツン)。
