# 探偵のお仕事(ショート動画)

縦型 1080x1920 / 30fps / 約42秒。完成品は `output/detective_short.mp4`。

- ナレーション: VOICEVOX:四国めたん(公開時はこのクレジット表記が必要)
- BGM: `bgm.py` で数値合成した自作曲(外部素材なし)
- 映像: `render.html` を Playwright で1フレームずつ撮影

## 作り直し

```
npm install
docker run -d -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
./build.sh
```

原稿は `narrate.py` の `LINES`、画面は `render.html` を編集する。
