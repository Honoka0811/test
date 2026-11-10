# ヒヨコ鑑定士 ショート動画

縦型（1080x1920, 30fps, 約30〜40秒）のショート動画を作るスクリプトです。

- 台本: `script.json`（`subtitle` は字幕、`voice` は読み上げ用のかな混じり文）
- ナレーション: VOICEVOX「四国めたん（ノーマル）」（speaker id 2）
- BGM: スクリプト内で合成するオリジナルのチップチューン（著作権の心配なし）
- 映像: Pillow で描いたヒヨコのイラストとテロップ

## 作り方

1. VOICEVOX エンジンを起動する（例: `docker run --rm -p 50021:50021 voicevox/voicevox_engine:cpu-latest`
   または公式リリースの `linux-cpu-x64/run`）
2. `python3 make_video.py` → `hiyoko_kanteishi_short.mp4` ができる

エンジンが無いときは `python3 make_video.py --no-voice` で映像と BGM だけを確認できます。

## クレジット

動画を公開するときは、概要欄などに `VOICEVOX:四国めたん` と記載してください（VOICEVOX の利用規約）。
