# 京都大学のここがすごい！10選（ショート動画）

- 完成動画: `kyoto_univ_sugoi10.mp4`（1080x1920 / 30fps / 約84秒）
- ナレーション: VOICEVOX:四国めたん（ノーマル）
- BGM・効果音: `render.py` 内で自作合成（著作権フリー）

## 作り直す手順
```sh
docker run -d --rm -p 50021:50021 voicevox/voicevox_engine:cpu-latest
python3 tts.py      # 台本(script.py) → 音声 build/voice/
python3 render.py   # 音声+BGM+映像 → kyoto_univ_sugoi10.mp4
python3 render.py 7 30   # 指定秒のプレビュー画像だけ出力
```
台本は `script.py`、読み間違いの補正は `tts.py` の `READING` で編集できます。
