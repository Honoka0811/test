# グリコ・森永事件 — ショート動画

昭和最大の未解決事件「グリコ・森永事件」(警察庁広域重要指定114号事件)を約79秒でたどる縦型ショート動画です
(1080×1920 / 30fps)。

- **完成動画: `output/glico_morinaga_short.mp4`**(ナレーション + BGM + 字幕焼き込み、-14 LUFS ステレオ)
- 字幕ファイル: `output/subtitles_ja.srt` / サムネイル: `output/thumbnail.jpg`
- タイトル・説明文・タグ案: `metadata.md`
- ナレーション: **VOICEVOX:四国めたん**(ノーマル)
- BGM: `bgm.py` で numpy 合成した自作曲(外部音源なし・権利フリー)。
  短2度でうなる低音ドローン、音程の揺れる壊れたオルゴール、心音、風のノイズ、シーン切替の衝撃音で不気味さを演出

## 構成

| # | シーン | 内容 |
|---|---|---|
| 0 | タイトル | 昭和最大の未解決事件 / 犯人 未逮捕 |
| 1 | 1984.3.18 | 江崎グリコ社長誘拐、現金10億円と金塊100kgを要求、3日後に自力脱出 |
| 2 | 挑戦状 | 「かい人21面相」を名乗り報道機関へ。「けいさつの あほども え」 |
| 3 | 毒入り菓子 | 丸大食品・森永製菓・ハウス食品などへ拡大、「どくいり きけん たべたら 死ぬで」 |
| 4 | キツネ目の男 | 現金受け渡し現場で目撃、あと一歩で取り逃がす |
| 5 | 1985.8 | 滋賀県警本部長の自殺、「くいもんの 会社 いびるの もお やめや」 |
| 6 | 2000.2.13 | 全事件の公訴時効成立、正体は今も闇の中 |
| 7 | クレジット | VOICEVOX:四国めたん / BGM 自作 |

## 再生成

```bash
python3 narrate.py   # ナレーション合成 → output/narration.wav, subtitles_ja.srt, timings.js(シーン尺・字幕タイミング)
node capture.js      # render.html を1フレームずつ撮影 → output/glico_morinaga_silent.mp4
python3 mix.py       # BGM生成 + ダッキング + 合成 + -14 LUFS 正規化 → output/glico_morinaga_short.mp4
```

- シーン尺はナレーションの長さから自動で決まります(原稿は `narrate.py` の `SCENES`)。
- `render.html` はブラウザで開くとプレビュー再生できます。
- 必要なもの: Node.js + Playwright(Chromium)、ffmpeg、IPA明朝/IPAゴシック、Python 3 + numpy + scipy + pyopenjtalk + voicevox_core

### VOICEVOX CORE

| 必要なもの | 取得元 | 環境変数(既定値) |
|---|---|---|
| `voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT` |
| `0.vvm`(四国めたん・ずんだもん等) | VOICEVOX/voicevox_vvm releases | `VOICEVOX_VVMS`(`/home/user/vv/vvms`) |

スタイルは `VOICEVOX_STYLE`(既定 2 = 四国めたん ノーマル。0 あまあま / 4 セクシー / 6 ツンツン)。
公開時は VOICEVOX 利用規約に従い「VOICEVOX:四国めたん」のクレジット表記が必要です(動画末尾と説明文に記載済み)。

## 注意

実在の事件を扱うため、内容は公開報道で広く知られている事実の概要に留め、特定の人物を犯人視する表現は入れていません。
「キツネ目の男」の人影は抽象的なシルエットで、似顔絵を再現したものではありません。
