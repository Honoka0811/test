# 総合商社のここがすごい（ショート動画）

縦型 1080x1920 / 30fps / 約51秒。完成品: `out/sogo_shosha_short.mp4`

- ナレーション: **VOICEVOX:四国めたん**（公開時はこのクレジット表記が必要。動画内にも表示済み）
- BGM・効果音: `build_audio.py` 内で合成した自作シンセ（素材の権利処理は不要）
- フォント: Dela Gothic One / Noto Sans JP（SIL OFL、Google Fonts から `fonts/` に配置）

## 再生成

```sh
# VOICEVOX ENGINE を 127.0.0.1:50021 で起動しておく
python3 build_audio.py   # ナレーション合成 + BGM ミックス -> build/
python3 render.py        # 映像描画 + エンコード -> out/
```

台本は `script.py`、画面構成は `render.py` の `scene_*` 関数。
