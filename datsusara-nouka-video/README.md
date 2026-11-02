# 脱サラして農家になる方法 ３選 — 解説動画

`datsusara_nouka_3sen.mp4`（1920×1080 / 30fps / 約9分40秒 / ナレーション・字幕・イラスト付き）

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

ナレーションはオフライン音声合成（Open JTalk / Mei）です。制度の金額・要件は年度により変わるため、動画内でも最新情報の確認を促しています。
