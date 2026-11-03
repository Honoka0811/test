# YouTube アップロード準備

## 投稿ファイル

| 用途 | ファイル | 備考 |
|---|---|---|
| 動画本体 | `drone_short_youtube.mp4` | 1080×1920 / 30fps / H.264 + AAC 48kHz。ラウドネスを YouTube 基準の -14 LUFS に調整済み |
| 字幕（日本語） | `drone_short.ja.srt` | 23キュー。ナレーションの文単位 |
| サムネイル（ショート用・縦） | `thumbnail_vertical.png` | 1080×1920 |
| サムネイル（通常動画用・横） | `thumbnail_16x9.png` | 1280×720 |
| メタデータ | `youtube_meta.json` | タイトル・説明文・タグ・カテゴリ・公開設定 |

## タイトル（40文字）

軍用ドローン、年に何機つくれる？ 生産力を国際比較【2026年版】#Shorts

## 説明文

`youtube_meta.json` の `snippet.description` をそのまま貼り付け（要点・注意書き・出典URL・クレジット・ハッシュタグ入り）。

## 設定

- カテゴリ: ニュースと政治
- 言語: 日本語（動画・音声とも）
- 公開設定: まず「非公開」でアップロードし、スタジオで確認してから公開に切り替える
- 子ども向け: いいえ
- 改変・合成コンテンツの開示: 「はい」を推奨（ナレーションが合成音声のため）
- ショート判定: 縦型かつ3分未満なので自動でショートになる。タイトルに #Shorts を含めてある
- 再生リスト: 任意

## アップロード方法

### A. ブラウザから手動（推奨）
1. YouTube Studio → 作成 → 動画をアップロード → `drone_short_youtube.mp4`
2. タイトル・説明文・タグを `youtube_meta.json` から貼り付け
3. サムネイルに `thumbnail_16x9.png`（ショートはアプリ側でフレーム選択になる場合あり）
4. 字幕 → 言語「日本語」→ ファイルをアップロード → `drone_short.ja.srt`
5. 「改変・合成コンテンツ」の開示にチェック
6. 非公開で保存 → 再生確認 → 公開

### B. スクリプトから（YouTube Data API）
```
pip install google-api-python-client google-auth-oauthlib
# Google Cloud Console で YouTube Data API v3 を有効化し、OAuth クライアント（デスクトップ）の client_secret.json をこのフォルダに置く
python upload_youtube.py            # 非公開でアップロード＋サムネイル＋字幕
python upload_youtube.py --public   # 公開で投稿
```
API 経由のアップロードは、Google Cloud プロジェクトが審査を通るまで動画が「非公開」に固定される場合があります。初回は A の手動アップロードが確実です。

## 公開前チェック

- [ ] 冒頭3秒で「年1,000万機 vs 年10万機」が見えている
- [ ] 「年」が「ねん」と読まれている（修正済み）
- [ ] BGM がナレーションを邪魔していない
- [ ] 末尾にクレジット「VOICEVOX:青山龍星」が表示されている
- [ ] 説明文に出典URLと「推計・目標値が混在」の注意書きがある
- [ ] 合成コンテンツの開示にチェック
