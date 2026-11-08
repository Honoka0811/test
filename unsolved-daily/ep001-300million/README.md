# 毎日の未解決事件 FILE No.001「三億円事件」— ショート動画

シリーズ「毎日の未解決事件」の第1話。縦型ショート(1080×1920 / 30fps / 58秒)、
ナレーションは **VOICEVOX:四国めたん**(ノーマル)、BGM・映像は自作(権利フリー)です。

- **アップロード用一式: `upload/`**(最終mp4・字幕SRT・サムネイルJPG・タイトル/説明文/タグ/運用メモの `metadata.md`)
- 完成動画(ナレーション+BGM): `output/unsolved_001_narrated.mp4`
- 無音・演出のみ: `output/unsolved_001_silent.mp4`
- 台本・構成・演出意図: `script.md`

## 視聴維持のための演出設計

| 仕掛け | 内容 |
|---|---|
| 2秒フック | 冒頭0.15秒で「たった3分で」→1.1秒で「3億円が消えた」を叩きつけ+赤「未解決」スタンプ+画面シェイク |
| 数字演出 | ストップウォッチ 0:00→3:00 と金額カウンター ¥0→¥300,000,000 が同時に回る |
| 心拍同期 | BGMの鼓動(60BPM)と画面周辺の明滅を同期 |
| 時間の可視化 | 上端に進行バー(残り時間が見えると離脱が減る) |
| 反転 | 「モンタージュ写真は無関係な人の顔」という意外な事実を後半に配置 |
| CTA | 「あなたの推理は?」コメント誘導+「毎日21時」フォロー導線 |
| 質感 | 雨パーティクル・フィルムグレイン・グリッチ・REC表示で"捜査資料"の没入感 |

## 再生成の方法

```bash
cd unsolved-daily/ep001-300million
node capture.js            # output/unsolved_001_silent.mp4(無音版)を生成
python3 narrate.py         # 四国めたんのナレーション+BGMダッキングで narrated.mp4 を生成
python3 bgm.py 58 output/bgm.wav  # BGMだけ書き出す場合
./export_upload.sh         # upload/ にアップロード用一式(-14 LUFS 正規化)
```

- `render.html` … Canvas 2D で `render(t)` が時刻 t 秒のフレームを決定論的に描画(ブラウザで開くとプレビュー再生)
- `capture.js` … Playwright(Chromium)で1フレームずつ撮影し、ffmpeg(libx264)にパイプして mp4 化
- `bgm.py` … サスペンスBGM(鼓動60BPM+秒針+低音ドローン+ライザー)を numpy だけで合成
- `narrate.py` … 台本を VOICEVOX(四国めたん ノーマル, style 2)で合成し、各キューに収まるよう話速を自動調整。BGMはナレーション中に自動ダッキング。`voicevox_core` が無い環境では Open JTalk にフォールバック
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、日本語フォント(IPAゴシック)、Python 3 + `numpy` + `pyopenjtalk`

### VOICEVOX のセットアップ

VOICEVOX CORE のリリースから以下を取得し、環境変数でパスを渡します(詳細な手順は
`pacific-war-analysis/README.md` と同じ)。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-…-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| `0.vvm`(四国めたん/ずんだもん等を含む) | VOICEVOX/voicevox_vvm releases(tag 0.17.1) | `VOICEVOX_VVMS` |
| Open JTalk 辞書 | `pyopenjtalk` 同梱を自動使用 | `VOICEVOX_DICT`(任意) |

音声を公開する場合は利用規約に従い **「VOICEVOX:四国めたん」のクレジット表記が必須**です
(動画末尾のカードと `upload/metadata.md` の概要欄に記載済み)。

## 事実関係・表現上の配慮

- 内容は公知の報道・資料に基づく概要で、数値(のべ捜査員約17万人、遺留品120点以上、容疑者リスト約11万人など)は資料により幅があるため概数として扱っています。
- 負傷者のいない時効成立事件を題材にし、実在個人の特定につながる表現は使っていません。
- シリーズ続編で被害者のいる事件を扱う場合は、遺族への配慮(実名・顔写真・茶化す演出を避ける等)を最優先してください。
