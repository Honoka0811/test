# 被害が大きかった日本本土空襲 — ショート動画

太平洋戦争末期(1944年11月〜1945年8月)の日本本土空襲のうち、特に被害が大きかったものを
数字でたどる縦型ショート動画(1080×1920 / 30fps / 67秒)です。
ナレーションは VOICEVOX:青山龍星、BGM は `bgm.py` によるプログラム生成(自作・権利フリー)。

| ファイル | 内容 |
|---|---|
| `output/air_raids.mp4` | 映像のみ(無音) |
| `output/bgm.wav` | BGMのみ |
| `output/subtitles_ja.srt` | 字幕 |
| `output/air_raids_narrated.mp4` | 完成版(ナレーション VOICEVOX:青山龍星 + BGM) |
| `output/narration.wav` | ナレーションのみ |
| **`upload/air_raids_final.mp4`** | **投稿用**(-14 LUFS に正規化・ステレオAAC) |

## 構成(67秒)

| 時間 | シーン | 内容 |
|---|---|---|
| 0:00–0:07 | タイトル | 日本本土空襲 被害が大きかった空襲 |
| 0:07–0:17 | B-29と作戦の変化 | マリアナ→東京 約2,300km / 昼間精密爆撃 → 夜間低空の焼夷弾攻撃 |
| 0:17–0:29 | 東京大空襲 1945.3.10 | 約300機 / 死者 約10万人 / 焼失 約27万戸 / 被災 約100万人 |
| 0:29–0:39 | 大都市への空襲 | 東京・大阪・名古屋・神戸の死者数比較 |
| 0:39–0:48 | 地方の中小都市へ | 約200都市が被災 / 富山 焼失率 約99.5% |
| 0:48–0:59 | 原子爆弾 | 広島 約14万人・長崎 約7万4千人(1945年末まで) |
| 0:59–1:07 | まとめ | 死者 約50万人以上 / 焼失家屋 約220万戸 / 約200都市 |

数値は資料によって幅があるため、動画内でも「概数・推計」と明記しています。
主な出典: 経済安定本部「太平洋戦争による我国の被害総合報告書」(1949)、東京都、広島市、長崎市、富山市ほか各自治体資料。

## 生成手順

```bash
node capture.js                 # render.html → output/air_raids.mp4(無音)
# 青山龍星の音声: VOICEVOX ENGINE を起動してから narrate.py を実行
docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
python3 narrate.py              # → output/air_raids_narrated.mp4(BGMダッキング付き)
./export_upload.sh             # → upload/ に投稿用一式
```

`narrate.py` は VOICEVOX ENGINE(HTTP, `VOICEVOX_URL`)→ voicevox_core の順に探し、
どちらも無い場合は停止します(`ALLOW_FALLBACK=1` で Open JTalk の仮音声プレビューを作成)。
投稿時は説明文に「VOICEVOX:青山龍星」のクレジットを入れてください(動画のエンドにも表記済み)。
