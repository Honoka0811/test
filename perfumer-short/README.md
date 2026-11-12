# 調香師のお仕事 — ショート動画

調香師(香りをつくる専門家)の仕事を紹介する縦型ショート動画です(1080×1920 / 30fps / 約72秒)。

- **完成動画: `output/perfumer_short.mp4`**(H.264 + AAC ステレオ、-14 LUFS に正規化済み)
- 字幕ファイル: `output/subtitles_ja.srt`(動画内にも字幕を焼き込み済み)
- サムネイル: `output/thumbnail.jpg`
- ナレーション: VOICEVOX 四国めたん(ノーマル)
- BGM: `bgm.py` で numpy だけで合成したオリジナル曲(Fメジャー/92BPM、エレピ+ベル+ベース+シェイカー)。外部音源なし
- フォント: Zen Maru Gothic(SIL Open Font License、`fonts/OFL.txt`)

## 構成

| シーン | 内容 |
|---|---|
| タイトル | 香水瓶のアニメーション「調香師ってどんな仕事?」 |
| 01 調香師とは? | 香水・シャンプー・洗剤・お菓子の香りも担当/パフューマーとフレーバリスト |
| 02 香りの材料 | 天然香料と合成香料、数千種類を嗅ぎ分けて記憶 |
| 03 香りのピラミッド | トップ/ミドル/ベースノート(読み上げに合わせて順に強調) |
| 04 仕事の流れ | イメージを聞く → 処方 → 調合 → ムエットで評価、を何百回も |
| 05 調香師になるには | 大学(化学など)→ 香料会社 → 約10年の修業 |
| まとめ | 「目に見えない香りで、人の心を動かす」+ クレジット |

## 公開するときの注意

VOICEVOX の利用規約により、**「VOICEVOX:四国めたん」のクレジット表記が必要**です(動画の最後に表示済み。説明文にも入れてください)。

説明文の例:

```
香水やシャンプーの香りは、だれが作っているの?
「調香師」というお仕事を約70秒で紹介します。

ナレーション:VOICEVOX:四国めたん
BGM:オリジナル

#調香師 #香水 #お仕事紹介 #仕事図鑑 #Shorts
```

## 作り直し方

```bash
./build.sh
```

1. `narrate.py` … `script.py` の原稿を VOICEVOX で合成。各文の長さからシーン尺を自動で決め、`output/timeline.js`(映像用)と SRT を書き出す
2. `capture.js` … `render.html`(Canvas 描画)を Playwright で1フレームずつ撮影して mp4 化
3. `mix.py` … BGM を生成し、ナレーション中は自動で音量を下げてミックス → -14 LUFS に正規化して合成

原稿を変えたいときは `script.py` を編集して `./build.sh` を再実行するだけで、シーン尺・字幕も追従します。
字幕用テキストの `|` は改行位置の候補です。`render.html` はブラウザで直接開くとプレビュー再生できます。

VOICEVOX CORE 0.17.1 のセットアップ(`/home/user/vv` 配下を想定、環境変数で変更可):
Python ホイール `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl`、ONNX Runtime `voicevox_onnxruntime-linux-x64-1.17.3`(`VOICEVOX_ORT`)、
音声モデル `0.vvm`(四国めたん含む、`VOICEVOX_VVMS`)、Open JTalk 辞書 `open_jtalk_dic_utf_8-1.11`(`VOICEVOX_DICT`)。
