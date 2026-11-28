# 冬に食べたいお鍋ランキング — ショート動画

独断と偏見で選んだ「冬に食べたいお鍋 TOP5」を、四国めたん(司会)とずんだもん(はしゃぎ役)の掛け合いで発表する縦型ショート動画です。
1080×1920 / 30fps / 約52秒 / H.264 + AAC ステレオ / -14 LUFS(YouTube ショート・TikTok・リール共通で使えます)。

- **完成動画: `output/winter_nabe_ranking.mp4`**
- サムネイル: `output/thumbnail.jpg`(字幕なし・タイトル画面)
- 字幕: `output/subtitles_ja.srt`
- 投稿用タイトル・説明文・タグ: `output/metadata.md`

## ランキングと構成

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00 | オープニング | ずんだもん「さむ〜い！」→ タイトルが落ちてきて「TOP5」シール、土鍋のフタがカタカタ |
| 0:06 | 第5位 豆乳鍋 | まろやか〜 / お肌ツヤツヤ / シメ▶チーズリゾット / ポカポカ度★3 |
| 0:12 | 第4位 もつ鍋 | ぷりっぷり！/ にんにくパワー / シメ▶ちゃんぽん麺 / ★4 |
| 0:18 | 第3位 寄せ鍋 | 具だくさん！/ なんでもアリ / シメ▶雑炊 / ★4 |
| 0:25 | 第2位 すき焼き | ジュワ〜ッ / ごはん泥棒 / シメ▶うどん / ★3(溶き卵の小鉢つき) |
| 0:32 | 発表前 | スポットライト+ドラムロール、フタがどんどん激しく揺れる |
| 0:37 | 第1位 キムチ鍋 | フラッシュ→フタが吹っ飛ぶ→ファンファーレ→紙吹雪・金の集中線・王冠 / シメ▶ラーメン＋チーズ / ★5 |
| 0:45 | まとめ | TOP5 一覧、「あなたの推し鍋はどれ？コメントで教えてね！」、フォロー誘導 |

順位はアンケート結果ではなく「独断と偏見」の企画です(動画内にも表示)。

## しくみ

すべて手元で生成しています(画像素材・音源素材は使っていません)。

| ファイル | 役割 |
|---|---|
| `script.py` | 台本(セリフ・ランキング)。VOICEVOX で掛け合い音声を合成し、各セリフ・演出の時刻を `build/timeline.json` / `timeline.js` に書き出す。料理名を言った瞬間に名前が出る、などの同期はここで決まる |
| `render.html` | Canvas 2D で `render(t)` が時刻 t のフレームを描く。鍋・具材(白菜・豚バラ・モツ・エビ・しいたけ・キムチ…)・湯気・泡・テロップもすべてコードで描画。ブラウザで開くとプレビュー再生、`?t=12.3` でその時刻に固定 |
| `capture.js` | Playwright(Chromium)で 1 フレームずつ撮影し ffmpeg で mp4 化。`--stills 1,8,40` で確認用静止画、`--thumb 5.6` でサムネイル |
| `audio.py` | BGM(F メジャー・136BPM の跳ねる 2 ビート。ベース・裏打ちコード・トイピアノ風メロディ・クラップ・そり鈴)と効果音(ドン！・ヒュン・ポン・ボヨン・カタカタ・ドラムロール・シンバル・ファンファーレ)を numpy で合成し、声が出ている間は BGM と長い効果音を下げてミックス |
| `make.sh` | 全工程を実行し、-14 LUFS / -1.5 dBTP に揃えて `output/` に書き出す |

### 再生成

```bash
cd winter-nabe-ranking
npm install          # フォント(Dela Gothic One, M PLUS Rounded 1c)
./make.sh            # 約3分。映像の撮影を飛ばすなら SKIP_VIDEO=1 ./make.sh
```

必要なもの: Node.js、`playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy` + `voicevox_core`。
VOICEVOX は次を GitHub リリースから取得し、`/home/user/vv` に置くか環境変数でパスを渡します。

| 必要なもの | 取得元 | 環境変数 |
|---|---|---|
| `voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl` | VOICEVOX/voicevox_core releases → `pip install` | — |
| `voicevox_onnxruntime-linux-x64-1.17.3.tgz` | VOICEVOX/onnxruntime-builder releases | `VOICEVOX_ORT`(`lib/libvoicevox_onnxruntime.so`) |
| `0.vvm`(四国めたん・ずんだもん) | VOICEVOX/voicevox_vvm releases(0.17.0) | `VOICEVOX_VVM` |
| `open_jtalk_dic_utf_8-1.11` | r9y9/open_jtalk releases | `VOICEVOX_DICT` |

セリフやランキングを変えたいときは `script.py` の `SCENES` / `DISHES` を書き換えて `./make.sh` を実行すれば、映像・字幕・効果音のタイミングもすべて自動で追従します。字幕の改行位置は `|` で指定します。

## クレジット

- 音声: VOICEVOX:四国めたん、VOICEVOX:ずんだもん(公開時は説明欄にもクレジットを記載してください。動画の最後にも表示済み)
- BGM・効果音・イラスト: 自作(権利フリー)
- フォント: Dela Gothic One、M PLUS Rounded 1c(いずれも SIL Open Font License)
