# 地球46億年を1年にすると — ショート動画

地球の歴史を1年のカレンダーに縮め、人類の登場(大晦日 23:26)と「あなたの一生=0.5秒」をオチにした縦型ショート(1080×1920 / 30fps / 約57秒)。

- **アップロード用一式: `upload/`**(`earth_calendar_final.mp4`・字幕 SRT・サムネイル・タイトル/説明文/タグの `metadata.md`)
- ナレーション: VOICEVOX:四国めたん(ノーマル)
- BGM・効果音: `bgm.py` でプログラム合成(権利フリー)
- フォント: `fonts/`(Dela Gothic One / M PLUS Rounded 1c、SIL OFL)

## 再生成

```bash
python3 narrate.py   # script.py の原稿を四国めたんで合成 → output/narration.wav, timings.json, subtitles_ja.srt
python3 bgm.py       # BGM・効果音を合成し、ダッキングしてミックス → output/mix.wav
node capture.js      # render.html をタイミングに合わせて描画 → output/video_silent.mp4
./export.sh          # 結合 + -14 LUFS 正規化 → upload/earth_calendar_final.mp4
```

VOICEVOX core 0.16.2 / voicevox_onnxruntime 1.17.3 / `0.vvm` / Open JTalk 辞書を `/home/user/vv/` に置く前提(パスは環境変数で変更可、`narrate.py` 冒頭参照)。
原稿を変えたら `narrate.py` から順に再実行すれば、映像も新しいタイミングに自動で合います。
