# YouTube アップロード準備キット

このフォルダだけで YouTube Shorts として投稿できる一式です。

| ファイル | 用途 |
|---|---|
| `30dai_yarubeki_10sen_youtube.mp4` | 投稿用マスター。YouTube 推奨設定（H.264 High / 2 B-frame / GOP 15 / bt709 / AAC-LC 384kbps 48kHz / moov 先頭）で再エンコード済み |
| `metadata.json` | タイトル（＋代替案3つ）、説明文、タグ、カテゴリ、言語、公開設定 |
| `captions_ja.srt` | 日本語字幕 29 キュー（ナレーションの音素タイミングから生成） |
| `thumbnail_9x16.png` | Shorts 用サムネイル（1080×1920） |
| `thumbnail_16x9.png` | 通常動画・SNS 共有用サムネイル（1280×720） |
| `upload_youtube.py` | YouTube Data API v3 でアップロード → サムネイル設定 → 字幕登録まで行うスクリプト |

## 手順A: YouTube Studio から手動で投稿（いちばん簡単）

1. [studio.youtube.com](https://studio.youtube.com) → 「作成」→「動画をアップロード」→ `30dai_yarubeki_10sen_youtube.mp4` を選択
2. タイトル・説明・タグを `metadata.json` からコピー（タイトル末尾の `#Shorts` は残す）
3. 「視聴者」→「いいえ、子ども向けではありません」
4. 「詳細設定」→ 字幕で `captions_ja.srt`（言語: 日本語）をアップロード、言語を「日本語」に設定
5. 「改変または合成されたコンテンツ」の申告: このナレーションは明らかな合成音声で、実在の人物・出来事を装っていないため、申告は不要と判断して `false` にしています（申告しても問題はありません）
6. 公開設定を選んで保存（まず「非公開」または「限定公開」で実機確認を推奨）
7. スマホの YouTube アプリから Shorts のサムネイルを `thumbnail_9x16.png` に変更可能（PC からは Shorts のカスタムサムネイルは設定できない場合があります）

## 手順B: スクリプトで投稿

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
# Google Cloud Console で YouTube Data API v3 を有効化し、OAuth クライアント（デスクトップ）の
# JSON をこのフォルダに client_secret.json として置く（詳細は upload_youtube.py 先頭）
python3 upload_youtube.py                       # 非公開でアップロード＋サムネ＋字幕
python3 upload_youtube.py --privacy public      # 即公開
python3 upload_youtube.py --publish-at 2026-11-05T19:00:00+09:00   # 予約公開
```

初回はブラウザで Google ログインが開きます。`client_secret.json` と `token.json` は `.gitignore` 済みなのでコミットされません。
API の動画アップロードは 1 本あたり 1,600 クォータ消費（デフォルト上限 10,000/日）なので、1 日数本までです。

## 投稿前チェックリスト

- [ ] 1080×1920・74 秒・9:16 で Shorts の条件（縦型・3 分以内）を満たしている → OK
- [ ] 音量: 統合ラウドネス約 -15.6 LUFS、ピーク -0.9 dBFS（YouTube の -14 LUFS 正規化で音量が持ち上がることはなく、歪みもない）
- [ ] スマホで一度再生し、字幕の読みやすさと BGM の大きさを確認する
- [ ] 説明文の「VOICEVOX：四国めたん」クレジットを削除しない（VOICEVOX 利用規約の表記義務）
- [ ] 公開時刻: 夜 19〜22 時台（日本時間）が Shorts では反応を取りやすい傾向
- [ ] 固定コメントで「あなたが 30 代でやってよかったことは？」と問いかけるとコメントが集まりやすい

## 素材ライセンス（説明文に記載済み）

- ナレーション: VOICEVOX：四国めたん（クレジット表記必須、商用利用可）
- イラスト: unDraw（MIT）／ 絵文字: Microsoft Fluent Emoji（MIT）
- BGM: パッヘルベル「カノン」のオリジナルアレンジ（楽曲はパブリックドメイン、音源 FluidR3_GM は MIT）。Content ID に抵触する既存録音は使っていません
