# 物価10年ショート動画

`bukka-10nen-shorts.mp4`：縦型 1080×1920、30fps、約54秒。ナレーションは VOICEVOX:青山龍星。

## 作り直し方

1. VOICEVOX エンジンを起動する：`docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest`
2. Noto Sans JP（500/900）と Noto Color Emoji を `<build>/fonts/` に置く（ファイル名は jp500.ttf, jp900.ttf, emoji.ttf）。
3. 次を順に実行する。
   ```
   python3 voice.py <build>/voice      # ナレーション合成＋タイムライン
   python3 cues.py  <build>            # 演出タイミング
   python3 audio.py <build>            # BGM・効果音（自作合成）＋ミックス
   node render.js   <build> out.mp4    # 映像描画＋エンコード
   ```

台本・価格・字幕は `script.json` で編集できます。BGM と効果音は numpy で合成したオリジナルなので、著作権の心配はありません。
価格は全国の目安となる概算です。
