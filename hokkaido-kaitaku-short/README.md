# 北海道開拓の現場に眠る骨 — ショート動画

「北海道の開拓現場には骨が埋まっている」という話を、実際に遺骨が見つかった現場(常紋トンネル・囚人道路・朱鞠内)でたどる
縦型ショート動画(1080×1920 / 30fps / 約59秒)です。ナレーションは VOICEVOX:四国めたん、BGM は自作です。

- **完成動画: `out/hokkaido_kaitaku_bones_short.mp4`**(H.264 + AAC ステレオ・-14 LUFS)
- 字幕: `out/subtitles_ja.srt` / サムネイル: `out/thumbnail.jpg`
- タイトル案・説明文・タグ・クレジット: `out/metadata.md`
- 音声素材: `audio/narration.wav`(ナレーションのみ)、`audio/bgm.wav`(BGM のみ)

## 構成

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00–0:07 | フック | 「人の骨が埋まっている」――ただの怪談? |
| 0:07–0:25 | 01 常紋トンネル | タコ部屋労働で100人以上が犠牲、1970年に壁の裏から人骨 |
| 0:25–0:40 | 02 囚人道路 | 1891年、網走〜北見峠 約160km、死者200人以上、鎖塚 |
| 0:40–0:48 | 03 朱鞠内 | 戦時中のダム・鉄道工事、笹やぶの下から遺骨 |
| 0:48–0:59 | まとめ | どこにでもあるわけではないが、忘れずにいたい |

原稿は `lines.json`(`text` = 字幕用、`read`/`kana` = 読み上げ用、`cap` = 画面字幕の改行と強調)。

## 内容について

- 人数・距離は資料によって幅があるため概数です(常紋トンネルの犠牲者は「百数十人」とする資料が多い、囚人道路の死者は211人とする資料が多い など)。
- 鎖塚の「鎖がついたままの骨」は現地に伝わる話に基づきます。動画の最後に「概数で、伝承を含みます」と明記しています。

## 素材とクレジット

| 素材 | 出典 | ライセンス |
|---|---|---|
| ナレーション | VOICEVOX:四国めたん(ノーマル) | VOICEVOX / 四国めたんの利用規約に従い、クレジット表記が必要 |
| `assets/jomon2.jpg` 常紋トンネル坑口 | Wikimedia Commons「Jōmon tunnel02.JPG」 | パブリックドメイン |
| `assets/jomon1.jpg` 常紋トンネル工事殉難者追悼碑 | Wikimedia Commons「Jōmon tunnel01.JPG」 | パブリックドメイン |
| `assets/kitamitoge.jpg` 中央道路開削殉難者慰霊の碑 | Wikimedia Commons「Kitami tōge01.JPG」 | パブリックドメイン |
| `assets/uryudam.jpg` 雨竜第一ダム | Wikimedia Commons「Uryu1-40-r1.JPG」 | パブリックドメイン |
| `assets/kiha40.jpg` 常紋トンネル付近の列車 | Wikimedia Commons「JR Hokkaido Kiha40 near Jomon tunnel 20200811 0918 30358.jpg」 | パブリックドメイン |
| 地図(北海道の輪郭) | Natural Earth(npm `world-atlas`) | パブリックドメイン |
| フォント | しっぽり明朝 B1 / Noto Sans JP | SIL OFL 1.1 |
| BGM | `bgm.py` で合成した自作曲 | 権利表記不要 |

囚人道路のルートは主要地点を結んだ概略図です。

## 再生成の方法

```bash
cd hokkaido-kaitaku-short
npm install                    # フォントと地図データ
docker run -d -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
node build_map.js              # map.js(北海道の輪郭)
python3 narrate.py             # audio/narration.wav・timeline.js・out/subtitles_ja.srt
node capture.js                # out/video_silent.mp4(無音)と out/thumbnail.jpg
python3 mix.py                 # BGM 合成 + ダッキング + -14 LUFS 正規化 → out/hokkaido_kaitaku_bones_short.mp4
```

- `render.html` … `render(t)` が時刻 t 秒の画面を決定論的に描く。ブラウザで開くとプレビュー再生、`?t=12.3` で静止
- `shot.js` … 指定した秒のフレームだけを書き出す確認用スクリプト
- 必要なもの: Node.js + `playwright`(Chromium)、`ffmpeg`、Python 3 + `numpy`、Docker(VOICEVOX ENGINE 用)
