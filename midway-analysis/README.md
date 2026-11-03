# ミッドウェー海戦 日本はどうすれば勝てたか — YouTube 解説動画

「暗号・兵力集中・索敵・即時発進・上空警戒」の5つの条件に絞って、図解でテンポよく解説する
横型動画(1920×1080 / 30fps / 約3分31秒)です。ナレーションは男性音声(VOICEVOX:青山龍星)、BGM は自作(権利フリー)です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグの `metadata.md`)
- 完成動画(正規化前): `output/midway_narrated.mp4`(再生成可能、git 管理外。配布用は `upload/` を使用)
- ナレーション音声のみ: `output/narration.wav`(`python3 narrate.py` で再生成、git 管理外)
- シーン尺・字幕タイミング: `output/timing.json`

## 構成(約3分31秒)

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00 | 導入 | 空母4隻喪失。しかし勝ち筋はあった |
| 0:15 | 両軍の戦力 | 日本 空母4 vs 米国 空母3 + ミッドウェー島航空隊 |
| 0:35 | 条件① 暗号を更新する | JN-25 の解読、暗号書更新の延期 |
| 0:59 | 条件② 戦力を分散しない | アリューシャン作戦、主力部隊が後方、瑞鶴不在(略地図) |
| 1:25 | 条件③ 索敵を厚くする | 索敵機7機、利根4号機の発進遅れ(扇形図) |
| 1:48 | 条件④ 積み替えずに今すぐ飛ばす | 兵装転換、山口多聞の具申、運命の5分間(時系列) |
| 2:27 | 条件⑤ 頭上を空にしない | 零戦が低空に引き寄せられ高高度ががら空き(側面図) |
| 2:48 | それでも戦争には勝てない | 空母保有数の推移、エセックス級 |
| 3:14 | まとめ | 5条件のおさらい + クレジット |

## 写真について

制作環境のネットワーク制限で Wikimedia Commons 等の写真サイトに接続できなかったため、現在の動画は**すべて自作の図解**で構成しています。
写真を差し込む構造は組み込み済みで、`photos/<scene id>.jpg`(scene id は `output/timing.json` 参照: hook, forces, code, concentrate, search, launch, cap, war, summary)を置いて
`node capture.js` を再実行すると、そのシーンの図解枠に写真(ゆっくりズーム)が表示されます。候補写真の検索語は `photos/manifest.json`、
Commons からの一括取得は `fetch_photos.sh` を参照してください(米海軍撮影のミッドウェー写真はパブリックドメインです)。

## 再生成の方法

```bash
cd midway-analysis
python3 narrate.py         # VOICEVOX でナレーション合成 → output/narration.wav, timing.json, subtitles_ja.srt, mix.wav(BGM込み)
node capture.js            # output/midway_silent.mp4 と output/thumbnail.png を生成(約10分)
ffmpeg -y -i output/midway_silent.mp4 -i output/mix.wav -c:v copy -c:a aac -b:a 192k -ac 2 -shortest -movflags +faststart output/midway_narrated.mp4
./export_upload.sh         # upload/ にアップロード用一式を書き出す(-14 LUFS 正規化)
```

- `narrate.py` … 原稿(`SCENES`)を文ごとに VOICEVOX(青山龍星 ノーマル, style 13, 話速 1.12)で合成し、文の長さからシーン尺と字幕タイミングを自動決定。BGM はナレーション中に自動で音量を下げてミックス(ダッキング)
- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(字幕・図解は timing.json に同期)。ブラウザで開くとプレビュー再生
- `capture.js` … Playwright(Chromium)で 1 フレームずつ撮影し ffmpeg(libx264)へパイプ。`--frames` で各文の代表フレームだけ PNG 出力(レイアウト確認用)
- `bgm.py` … ドキュメンタリー風BGM(Dマイナー 72BPM)を numpy だけで合成。外部音源不使用
- 必要なもの: Node.js + `playwright`(Chromium), `ffmpeg`, 日本語フォント(IPAゴシック), Python 3 + `numpy` + `voicevox_core`

### VOICEVOX のセットアップ

| 必要なもの | 取得元 | 既定パス / 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`lib/libvoicevox_onnxruntime.so`) |
| `15.vvm`(青山龍星) | VOICEVOX/voicevox_vvm releases (tag 0.17.1) | `VOICEVOX_VVMS`(置いたディレクトリ) |
| Open JTalk 辞書 `open_jtalk_dic_utf_8-1.11` | r9y9/open_jtalk releases | `VOICEVOX_DICT` |

VOICEVOX の音声を公開する場合は「VOICEVOX:青山龍星」のクレジット表記が必要です(動画末尾と `upload/metadata.md` に記載済み)。

## 内容の根拠(概数)

- 索敵機7機・利根4号機の発進遅延(約30分)、7:28 の敵艦隊発見報告、山口多聞の「現装備ノママ直チニ発進ノ要アリト認ム」、10:20 前後の急降下爆撃による赤城・加賀・蒼龍の被弾: 各種戦史(戦史叢書、Parshall & Tully *Shattered Sword* ほか)
- 暗号書更新の延期(5月→6月): 米側の JN-25 解読史に関する各種資料
- 空母保有数の推移: `pacific-war-analysis/README.md` と同じ概数データ
