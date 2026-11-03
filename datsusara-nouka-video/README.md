# 脱サラして農家になる方法 ３選 — 解説動画

`datsusara_nouka_3sen.mp4`（1920×1080 / 30fps / 約4分50秒 / ナレーション・字幕・イラスト付き）

## 構成
1. タイトル
2. はじめに（この動画の流れ）
3. 基礎知識（農地法・相談窓口）
4. 方法① 新規就農（概要 / 流れ / 支援制度）
5. 方法② 雇用就農（概要 / 求人の探し方）
6. 方法③ 親元就農・第三者継承（概要 / 仕組み）
7. ３ルート比較表
8. 共通ポイント４つ
9. まとめ

## 作り方（再生成）
```bash
pip install pyopenjtalk numpy pillow   # Node 側は playwright + Chromium、ffmpeg が必要
python3 build.py <作業ディレクトリ> <出力mp4パス>
```
- `script.py` … 台本（箇条書き＋ナレーション）
- `illustrations.py` … SVG イラスト部品とシーン
- `build.py` … HTML 生成 → Playwright で画像化 → Open JTalk で音声合成 → ffmpeg で合成
- `render.js` … スライド画像化（Playwright）

## ナレーション（音声合成）
既定は **VOICEVOX（四国めたん）** です。クレジット表記「VOICEVOX:四国めたん」が必要なため、動画末尾に記載しています。
- VOICEVOX を使うには `vv/` に VOICEVOX ONNX Runtime（`ort/lib/libvoicevox_onnxruntime.so*`）と音声モデル（`models/*.vvm`）を置き、`voicevox_core` の wheel を pip で入れます（いずれも GitHub の VOICEVOX リリースから取得。容量が大きいため git には含めていません。`VV_DIR` で別の場所も指定可）。
- 環境変数 `VOICE` で声を切り替えられます：`metan` / `zundamon` / `tsumugi` / `himari` / `sora` / `no7` / `kiritan` / `mochiko`（VOICEVOX）、`happy` / `neutral`（Open JTalk + 東北大学 tohoku-f01, CC BY 4.0, `voices/` 同梱）、`mei`（Open JTalk 同梱）。
- `voice_samples/` に各声の比較サンプルがあります（`vv_*.mp3` が VOICEVOX）。
- 音声モデルの利用規約は VOICEVOX 公式（https://voicevox.hiroshiba.jp/ および各キャラクターの規約）に従ってください。
