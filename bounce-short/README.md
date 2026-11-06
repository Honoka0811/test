# Every Bounce = Bigger Ball — YouTube Shorts

円の中で跳ねるたびにボールが3%ずつ大きくなり、円を埋め尽くすまでを見せる
「気持ちいい系」物理シミュレーションのショート動画(1080×1920 / 60fps / 33.9秒)。
映像も音もすべてコードで生成しており、外部素材は使っていません。

- **アップロード用一式: `upload/`**(最終mp4・サムネイル・タイトル/説明文/タグ/戦略の `metadata.md`)
- 元動画: `output/every_bounce_bigger.mp4` / バウンド音のみ: `output/bounce.wav`

## 構成
| 時間 | 内容 |
|---|---|
| 0:00 | 「EVERY BOUNCE = BIGGER BALL / Will it fill the circle?」で問いを提示 |
| 0:00–0:30 | 71回バウンド。毎回ペンタトニックの音が鳴り、サイズに応じて音程が上がる。終盤ほど間隔が詰まり加速 |
| 0:30 | 「FILLED!」+ 和音 |
| 0:31–0:34 | 「71 bounces. Watch again?」でループ誘導 |

## 再生成
```bash
cd bounce-short
python3 sim.py          # 尺とバウンド数の確認
python3 render.py       # output/every_bounce_bigger.mp4 を生成(約1.5分)
./export_upload.sh      # upload/ に -14 LUFS 正規化版とサムネイルを書き出し
```
- `sim.py` … 決定論的な物理シミュレーション(重力・円形壁での反射・バウンドごとに拡大)
- `render.py` … Pillow でフレーム描画 → ffmpeg にパイプ。音は numpy で合成(自作モチーフ+クリック音+簡易リバーブ)
- `thumbnail.py` … サムネイル生成
- 必要なもの: Python 3 + numpy + Pillow, ffmpeg
