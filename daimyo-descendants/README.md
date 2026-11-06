# 江戸時代の大名の子孫は今なにしてる？ — YouTube 動画

江戸時代の大名家 9 家の子孫の「今」を紹介する横型動画(1920×1080 / 30fps / 約3分10秒)。
ナレーションは VOICEVOX の **四国めたん**(ノーマル)、BGM は numpy で合成した自作の和風ローファイ(権利フリー)。

- 原稿・登場人物データ: `script.json`(字幕表示用と読み上げ用のテキストを行ごとに持つ)
- 投稿用タイトル・概要欄(出典)・タグ・伸ばすための施策: `metadata.md`

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00 | オープニング | 「総理大臣、大学教授、宇宙の研究者まで」 |
| 0:12 | 前提 | 1869 華族に → 1871 廃藩置県 → 1947 華族制度廃止 |
| 0:31 | 其の一 徳川宗家 | 徳川家広さん(19代当主・評論家/翻訳家) |
| 0:46 | 其の二 尾張徳川家 | 徳川義崇さん(徳川美術館 館長) |
| 1:01 | 其の三 島津家 | 島津忠裕さん(島津興業で経営・神職) |
| 1:17 | 其の四 伊達家 | 伊達泰宗さん(瑞鳳殿 館長などを歴任) |
| 1:31 | 其の五 真田家 | 眞田幸俊さん(慶應義塾大学 理工学部 教授) |
| 1:46 | 其の六 上杉家 | 上杉邦憲さん(宇宙工学者・JAXA 名誉教授) |
| 2:01 | 其の七 徳川慶喜家 | 徳川慶朝さん(写真家・徳川将軍珈琲、2017年没) |
| 2:17 | 番外編 有馬家 | 有馬頼寧と「有馬記念」 |
| 2:32 | 其の八 細川家 | 細川護熙さん(元総理大臣 → 陶芸家) |
| 2:53 | まとめ | コメント誘導・チャンネル登録・クレジット |

(時刻は見積もり。VOICEVOX 合成後に `python3 chapters.py` で確定値を出力)

## 事実確認の方針

- 公開資料・報道で裏付けが取れた肩書のみ使用。画面と概要欄に「肩書は公開資料・報道時点のもの」と明記
- 当主の代数が資料で食い違う家(伊達家・上杉家・真田家)は代数を出さない
- 裏付けが取れなかった家(井伊家など)は不採用
- 実在人物の写真は使わない。家紋風マークは家名の一文字を丸で囲んだイメージ(実際の家紋ではない)

## ビルド

```bash
./build.sh            # 完成版: VOICEVOX 合成 → 映像撮影(4並列) → BGMミックス(-14 LUFS) → サムネイル
./build.sh --preview  # VOICEVOX なしのプレビュー(尺は見積もり、BGM のみ)
python3 chapters.py   # 概要欄用の目次を出力
```

出力(`output/`):`daimyo_descendants.mp4`(完成版)/ `preview_no_voice.mp4`(プレビュー)/ `subtitles_ja.srt` / `thumbnail.png` / `timeline.json`

- `narrate.py` … `script.json` を行単位で合成し、字幕と音声のタイミングを `timeline.json` に書き出す(映像はこれに同期)
- `render.html` … Canvas 2D で `render(t)` が時刻 t のフレームを決定論的に描画
- `capture.js` … Playwright で撮影 → ffmpeg。`--stills 10,40` で確認用静止画、`--thumb` でサムネイル
- `bgm.py` … D の陽音階・90BPM の和風ローファイ(琴風メロディ+エレピ+ベース+ビート)
- `mix.py` … 発話区間で BGM を自動で下げてミックスし、-14 LUFS に正規化して映像と合成
- フォント: `./fetch_fonts.sh` で Google Fonts から取得(しっぽり明朝 B1 / Zen角ゴシック New、OFL)

### VOICEVOX(四国めたん)のセットアップ

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| `0.vvm`(四国めたん・ずんだもん) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS` |
| Open JTalk 辞書 | `pip install pyopenjtalk` 同梱 | `VOICEVOX_DICT`(任意) |

声色は `VOICEVOX_STYLE`(2 = ノーマル、0 = あまあま、6 = ツンツン)、話速は `VOICEVOX_SPEED`(既定 1.15)で変更可。
公開時は利用規約に従い「VOICEVOX:四国めたん」のクレジットが必要(エンドカードと概要欄に記載済み)。
