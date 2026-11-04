# 富士フイルムの化粧品事業 解説動画

`fujifilm_cosmetics.mp4` は、富士フイルムの化粧品事業（アスタリフト等）を約3分でテンポよく解説するYouTube向け動画です。

- 解像度 1920x1080 / 30fps / H.264 + AAC
- ナレーション：VOICEVOX 0.26.1「青山龍星（ノーマル）」（speedScale 1.12）
- BGM：`make_bgm.py` で numpy 合成したオリジナル曲（権利関係なし）
- 図版：`render_slides.py` で Pillow 描画したオリジナルイラスト（実写写真は未使用）
- 字幕：ナレーション文ごとに自動で焼き込み（ASS）
- 演出：箇条書きはナレーションに合わせて1つずつ表示、セクション区切りカード、画面下の進捗バー、ポップ音／スウッシュ音
- 付属：`thumbnail.png`（サムネイル）、`chapters.txt`（チャプター）、`youtube_description.md`（概要欄）
- 台本：`script.md`

## 再生成の手順

```bash
# 1. VOICEVOX エンジンを起動（Linux CPU 版を展開した場合）
./run --host 127.0.0.1 --port 50021

# 2. フォント（Noto Sans CJK JP の Regular/Bold/Black .otf）を fonts/ に置く

# 3. スライド → ナレーション → 動画
python3 render_slides.py fonts out/slides
python3 make_voice.py out/voice
python3 build_video.py out/slides out/voice out/work fujifilm_cosmetics.mp4
```

内容（見出し・要点・ナレーション）は `scenario.py` を編集すると差し替わります。

## クレジット表記（YouTube 概要欄用）

```
ナレーション：VOICEVOX:青山龍星
```
