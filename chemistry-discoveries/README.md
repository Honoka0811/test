# 世界を変えた化学の大発見 6選 — ショート動画

縦型ショート動画(1080×1920 / 30fps / 約69秒)。ナレーションは VOICEVOX:四国めたん(ノーマル)、BGM は自作(numpy で合成、権利フリー)、字幕は動画に焼き込み済み。

- **完成動画: `output/chemistry_discoveries.mp4`**(H.264 + AAC ステレオ、-14 LUFS 正規化済み)
- 字幕ファイル: `output/subtitles_ja.srt`(YouTube に別途アップロードする場合)
- サムネイル: `output/thumbnail.jpg`

## 構成

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00 | タイトル | 世界を変えた化学の大発見 6選 |
| 0:06 | No.1 1869年 周期表 | メンデレーエフ。未発見元素(ガリウム・ゲルマニウム)を予言 |
| 0:15 | No.2 1898年 放射能とラジウム | キュリー夫妻。ポロニウム・ラジウムを発見 → がん治療・原子力 |
| 0:24 | No.3 1909年 アンモニア合成 | ハーバー(のちボッシュが工業化)。世界人口の約半分の食料を支える(推計) |
| 0:36 | No.4 1928年 ペニシリン | フレミング。アオカビの周りで細菌が消える → 人類初の抗生物質 |
| 0:45 | No.5 1935年 ナイロン | カロザース。合成繊維・プラスチックの時代へ |
| 0:53 | No.6 1985年 リチウムイオン電池 | 吉野彰(2019年ノーベル化学賞)。スマホ・電気自動車 |
| 1:02 | まとめ | 6つの発見の一覧 + クレジット |

「世界人口の約半分」は Erisman et al., *Nature Geoscience* (2008) の推計に基づく(動画内にも「推計」と表記)。

## 投稿用メタデータ(例)

**タイトル**: 世界を変えた化学の大発見6選【周期表からリチウムイオン電池まで】 #Shorts

**説明文**:
```
人類の暮らしを変えた化学の大発見を、四国めたんが6つ紹介します。

1869 周期表(メンデレーエフ)
1898 放射能・ラジウム(キュリー夫妻)
1909 アンモニア合成(ハーバー・ボッシュ法)
1928 ペニシリン(フレミング)
1935 ナイロン(カロザース)
1985 リチウムイオン電池(吉野彰)

▼クレジット
ナレーション: VOICEVOX:四国めたん
BGM: 自作(権利フリー)

#化学 #科学 #雑学 #歴史 #ノーベル賞 #Shorts
```

**タグ**: `化学,科学,大発見,周期表,メンデレーエフ,キュリー夫人,ラジウム,ハーバーボッシュ法,ペニシリン,フレミング,ナイロン,リチウムイオン電池,吉野彰,ノーベル賞,雑学,VOICEVOX,四国めたん,Shorts`

VOICEVOX の音声を公開する場合は「VOICEVOX:四国めたん」のクレジット表記が必要です(動画の最後と説明文に記載済み)。

## 再生成の方法

```bash
cd chemistry-discoveries
./build.sh
```

1. `narrate.py` … 原稿(`SCRIPT`)を VOICEVOX で合成し、**ナレーションの長さからシーン尺を自動決定**して `timeline.js`(シーン時刻・字幕)、`output/narration.wav`、`output/subtitles_ja.srt` を書き出す
2. `capture.js` … `render.html`(Canvas 2D、`render(t)` で時刻 t のフレームを決定論的に描画)を Playwright で 1 フレームずつ撮影し、ffmpeg で `output/video_silent.mp4` に
3. `mix.py` … `bgm.py` の BGM(Cメジャー・104BPM、マリンバ風アルペジオ+ベル+パッド+ベース+軽いリズム)を、発話中は自動で下げて(ダッキング)ミックスし、-14 LUFS に正規化して最終 mp4 を出力

原稿を書き換えて `./build.sh` を再実行すれば、シーン尺も字幕も自動で追従します。`render.html` をブラウザで直接開くとプレビュー再生できます。

### 必要なもの

Node.js + `playwright`(Chromium)、`ffmpeg`、IPAゴシックフォント、Python 3 + `numpy` + `pyopenjtalk`(辞書用)+ `voicevox_core`。

| 必要なもの | 取得元 | 環境変数(既定値は `/home/user/vv/...`) |
|---|---|---|
| `voicevox_core-0.16.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| 音声モデル `0.vvm`(四国めたん) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS` |

スタイル変更は `VOICEVOX_STYLE=0 ./build.sh`(0 = あまあま、6 = ツンツン、4 = セクシー。既定 2 = ノーマル)。
