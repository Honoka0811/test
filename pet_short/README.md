# ペット生涯コストランキング（ショート動画）

- `pet_cost_ranking_short.mp4`：縦型 1080x1920 / 30fps / 約72秒
- ナレーション：VOICEVOX:四国めたん
- BGM・効果音：`src/audio_gen.py` でプログラム生成したオリジナル音源
- 絵文字画像：Twemoji（© Twitter, Inc. and other contributors / CC-BY 4.0）
- フォント：Dela Gothic One、M PLUS Rounded 1c（SIL OFL 1.1）

## 投稿時の概要欄に入れるクレジット（例）
```
ナレーション：VOICEVOX:四国めたん
絵文字：Twemoji (CC-BY 4.0)
※金額は目安です（ペットフード協会の調査等をもとにした概算）
```

## 作り直す手順（src/）
1. VOICEVOXエンジンを `127.0.0.1:50021` で起動
2. `python3 synth.py` → ナレーション合成と `timing.json` 作成
3. `python3 audio_gen.py audio <秒数>` → BGM・効果音
4. `python3 mix.py` → 音声ミックス
5. `python3 render.py out.mp4` → 映像を書き出し、ffmpegで音声と合成
