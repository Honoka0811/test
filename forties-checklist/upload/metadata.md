# アップロード用メタデータ(YouTube Shorts)

## ファイル(検証済み)
| ファイル | 内容 | YouTube 要件との照合 |
|---|---|---|
| `forties_checklist_final.mp4` | 1080×1920 / 30fps / 69.6秒 / H.264 High + AAC-LC 48kHz ステレオ / 17.1MB / -14.1 LUFS | 縦型・3分以内 → ショート判定 OK。推奨コーデック・faststart 済み |
| `thumbnail.jpg` | 1080×1920 JPEG / 231KB | 2MB 以下 OK(ショートのサムネイルはスマホ版 YouTube アプリでのみ変更可。PC の Studio では動画内フレームから選ぶ) |
| `subtitles_ja.srt` | 日本語字幕 12 キュー | Studio の「字幕」からアップロード可(焼き込み字幕があるので任意) |
| `youtube_metadata.json` | タイトル・説明文・タグ・カテゴリ(27 教育)・言語(ja)・公開設定(非公開) | タイトル 35/100 文字、説明文 5000 文字以内、タグ合計 500 文字以内 |
| `upload_youtube.py` | YouTube Data API でアップロードするスクリプト(`--dry-run` で検証のみ) | 下記「アップロード手順 B」 |

## アップロード手順 A(手動・YouTube Studio、いちばん確実)
1. https://studio.youtube.com → 右上「作成」→「動画をアップロード」→ `forties_checklist_final.mp4` を選ぶ
2. 詳細: タイトル・説明文・タグを `youtube_metadata.json`(または下記)からコピー。「視聴者」は「いいえ、子ども向けではありません」
3. 「詳細設定」: カテゴリ「教育」、動画の言語「日本語」、字幕 → `subtitles_ja.srt` をアップロード(任意)
4. 動画の要素: ショートには終了画面・カードは付かないのでスキップ
5. チェック: 著作権の警告が出ないことを確認(BGM は自作演奏なので通常は出ない)
6. 公開設定: まず「非公開」または「限定公開」で保存してスマホで再生確認 → 問題なければ「公開」または「スケジュール設定」
7. サムネイルを差し替える場合はスマホの YouTube アプリ → 自分の動画 → 編集 → サムネイルから `thumbnail.jpg` を選ぶ

## アップロード手順 B(スクリプト・YouTube Data API)
```bash
pip install google-api-python-client google-auth-oauthlib
# Google Cloud Console で YouTube Data API v3 を有効化し、OAuth クライアント ID(デスクトップ)の JSON を
# upload/client_secret.json として置く(OAuth 同意画面のテストユーザーに自分のアカウントを追加)
cd forties-checklist/upload
python3 upload_youtube.py --dry-run                       # 検証のみ
python3 upload_youtube.py                                 # 非公開でアップロード + サムネイル + 字幕
python3 upload_youtube.py --publish-at 2026-11-05T21:00:00+09:00   # 予約公開
```
- 初回はブラウザが開き Google ログインと許可を求められる。トークンは `token.json` に保存(どちらも .gitignore 済み)
- Google の審査を受けていない API プロジェクトからのアップロードは非公開に固定されるため、公開は Studio から行う
- 1 回のアップロードで API クォータ約 1,600 ユニット消費(1 日の無料枠 10,000)

- `forties_checklist_final.mp4` … 本編(1080×1920 / 30fps / 約70秒 / -14 LUFS)
- `subtitles_ja.srt` … 日本語字幕(焼き込み済みの字幕と同内容。CC として追加する場合に)
- `thumbnail.jpg` … サムネイル(縦 9:16)

## タイトル(確定)
40代のうちにやっておくべきこと10選【テンポよく解説】#Shorts

別案
1. 40代のうちにやっておくべきこと10選【テンポよく解説】
2. 【保存版】40代で絶対やっておきたい10のこと
3. 50代になって後悔しないために。40代でやるべき10選

## 説明文
40代のうちにやっておくべきことを10個、テンポよくまとめました。
健康・お金・学び・人間関係・挑戦。全部やらなくて大丈夫、まずは1つから。

00:00 タイトル
00:03 ① 毎年の健康診断
00:09 ② 運動を習慣にする
00:16 ③ 歯のメンテナンス
00:22 ④ 睡眠と食事の見直し
00:28 ⑤ 老後資金の計画
00:34 ⑥ 学び直し
00:41 ⑦ 親と話しておく
00:46 ⑧ 人間関係の整理
00:52 ⑨ やりたかったことに挑戦
00:58 ⑩ 持ち物と保険の見直し
01:03 まとめ

ナレーション: VOICEVOX:四国めたん
イラスト: unDraw(undraw.co)
絵文字: Fluent Emoji(Microsoft, MIT License)
BGM: パッヘルベル「カノン」自作アレンジ(音源 GeneralUser GS)

※ 本動画は一般的な情報の紹介です。健康・お金に関する判断は専門家にご相談ください。

## タグ
40代, アラフォー, 40代でやるべきこと, 人生設計, 健康診断, 筋トレ, 老後資金, 新NISA, iDeCo, 学び直し, リスキリング, 人間関係, 断捨離, ライフハック, 自己啓発, VOICEVOX, 四国めたん, Shorts

## ハッシュタグ(ショート用)
#Shorts #40代 #アラフォー #人生 #ライフハック #VOICEVOX #四国めたん

## 公開前チェックリスト
- [x] 縦型 9:16・69.6 秒(YouTube Shorts は 3 分まで。TikTok/Instagram リールにもそのまま使える)
- [x] 説明文に「VOICEVOX:四国めたん」のクレジット(VOICEVOX 利用規約)
- [x] 音量 -14.1 LUFS / ピーク -1.4 dBFS(export_upload.sh で計測)
- [x] タイトル・説明文に #Shorts
- [x] 子ども向けではない / カテゴリ「教育」/ 言語「日本語」
- [ ] スマホで再生して字幕が UI(右側のボタン・下部のタイトル)に隠れないか確認
- [ ] 非公開で確認後に公開 or 予約公開(日本向けなら平日 19〜22 時、週末は昼が目安)
- [ ] 公開後: 固定コメントに「あなたが40代でやってよかったことは?」のように質問を置くとコメントが付きやすい
