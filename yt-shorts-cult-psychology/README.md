# YouTubeショート「なぜ普通の人が新興宗教にハマるのか」

心理学ベースの注意喚起系ショート動画（約55秒・1080x1920・30fps）。
完成品は `out/shorts_cult_psychology.mp4`。台本・演出・投稿用メタデータは `script.md`。

## 構成ファイル

- `script.md` — 台本・演出意図・タイトル案・説明文・固定コメント（CTA回収用）
- `build.py` — 全自動生成パイプライン（音声合成→字幕→BGM→動画）
- `out/shorts_cult_psychology.mp4` — 完成動画
- `out/subs.ass` — 焼き込み済み字幕（手直しして再レンダリング可能）

## 技術構成

| 要素 | 実装 |
|---|---|
| ナレーション | VOICEVOX CORE 0.17.1 / 四国めたん（ノーマル id=2、ヒソヒソ id=37） |
| BGM | numpyで合成（72BPM心音・ダークパッド・秒針・シーン切替ブーム）→ 著作権フリー |
| 音声ミックス | ffmpeg sidechaincompress でBGMを自動ダッキング、-14 LUFSに正規化 |
| 映像 | ffmpeg lavfi（動く深紅グラデ＋グレイン＋ビネット＋明滅）＋ASS字幕 |
| フォント | Noto Sans CJK JP Black（SIL OFL） |

## 再生成方法

VOICEVOXアセット（コアwheel・ONNX Runtime・Open JTalk辞書・0.vvm/5.vvm）と
Noto Sans CJK JP Black/Bold を用意して:

```bash
pip install https://github.com/VOICEVOX/voicevox_core/releases/download/0.17.1/voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
VVX_ORT=/path/to/libvoicevox_onnxruntime.so \
VVX_DICT=/path/to/open_jtalk_dic_utf_8-1.11 \
VVX_VVM=/path/to/vvms \
FONTS_DIR=~/.fonts \
python3 build.py
```

## 公開時の注意

- **クレジット必須**: 動画説明文に「VOICEVOX:四国めたん」（動画右下にも焼き込み済み）
- 特定の宗教団体名は出していません（名誉毀損・コミュニティガイドラインのリスク回避のため、追記しないこと推奨）
- 投稿後すぐに `script.md` の「固定コメント用」をコメント欄に固定する（動画内CTAの回収）
- 伸ばすコツ: 同フォーマットで「マルチ商法」「占い詐欺」「情報商材」など横展開してシリーズ化すると回遊が生まれる
