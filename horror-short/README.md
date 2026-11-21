# horror-short

チャット型ホラーのショート動画(1080x1920 / 30fps / 42秒)。映像は `scene.html` をヘッドレスブラウザでコマ撮り、音は `audio.py` で全て合成。

- #1 完成品: `horror_short.mp4`(台本 `timeline.json`)
- #2 完成品: `horror_short_2.mp4`(台本 `timeline2.json`)
- 緊急放送編 完成品: `horror_tv.mp4`(台本 `tv.json` / 画面 `scene_tv.html` / 音 `audio_tv.py`、ビルドは `./build.sh tv.json horror_tv.mp4`)
- 位置情報アプリ編 完成品: `horror_map.mp4`(台本 `map.json` / 画面 `scene_map.html` / 音 `audio_map.py`、ビルドは `./build.sh map.json horror_map.mp4`)
- 聴力検査編 完成品: `horror_ear.mp4`(台本 `ear.json` / 画面 `scene_ear.html` / 音 `audio_ear.py`、ビルドは `./build.sh ear.json horror_ear.mp4`)
- 昔話・神隠し編 完成品: `horror_kami.mp4`(台本 `kami.json` / 画面 `scene_kami.html` / 音 `audio_kami.py`、ビルドは `./build.sh kami.json horror_kami.mp4`)
- 昔話・盆踊り編 完成品: `horror_bon.mp4`(台本 `bon.json` / 画面 `scene_bon.html` / 音 `audio_bon.py`、ビルドは `./build.sh bon.json horror_bon.mp4`)
- 台本ファイルを書き換えるとセリフ・間・相手の名前・配色を変更できる
- 再ビルド: `npm install && ./build.sh timeline2.json horror_short_2.mp4`(引数なしで #1)
