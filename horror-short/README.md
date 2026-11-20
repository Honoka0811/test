# horror-short

チャット型ホラーのショート動画(1080x1920 / 30fps / 42秒)。映像は `scene.html` をヘッドレスブラウザでコマ撮り、音は `audio.py` で全て合成。

- #1 完成品: `horror_short.mp4`(台本 `timeline.json`)
- #2 完成品: `horror_short_2.mp4`(台本 `timeline2.json`)
- 台本ファイルを書き換えるとセリフ・間・相手の名前・配色を変更できる
- 再ビルド: `npm install && ./build.sh timeline2.json horror_short_2.mp4`(引数なしで #1)
