# -*- coding: utf-8 -*-
"""YouTube Data API v3 で upload/ の動画を投稿する(動画本体 + サムネイル + 日本語字幕)。
メタデータは upload/youtube.json から読む。

準備(初回のみ):
  1. Google Cloud Console でプロジェクトを作り「YouTube Data API v3」を有効化
  2. OAuth クライアント ID(種類: デスクトップ アプリ)を作成し、client_secret.json をこのディレクトリに保存
     (OAuth 同意画面がテスト状態の場合は、自分の Google アカウントをテストユーザーに追加)
  3. pip install google-api-python-client google-auth-oauthlib

使い方:
  python3 youtube_upload.py                      # youtube.json の設定どおり(既定は非公開)で投稿
  python3 youtube_upload.py --privacy public     # 公開で投稿
  python3 youtube_upload.py --publish-at 2026-11-05T12:00:00+09:00   # 公開予約(非公開で投稿し、指定時刻に公開)
  python3 youtube_upload.py --dry-run            # 送信内容の確認のみ

初回実行時にブラウザが開き Google アカウントの認可を求められる。トークンは token.json に保存され、次回以降は再認可不要。
注意: 投稿はチャンネルの API クォータ(1日 10,000 ユニット、動画1本の投稿で約1,600)を消費する。
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(HERE, 'upload')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

ap = argparse.ArgumentParser()
ap.add_argument('--meta', default=os.path.join(UPLOAD, 'youtube.json'))
ap.add_argument('--client-secret', default=os.environ.get('YT_CLIENT_SECRET', os.path.join(HERE, 'client_secret.json')))
ap.add_argument('--token', default=os.path.join(HERE, 'token.json'))
ap.add_argument('--privacy', choices=['private', 'unlisted', 'public'], help='youtube.json の privacyStatus を上書き')
ap.add_argument('--publish-at', help='公開予約時刻(RFC3339、例 2026-11-05T12:00:00+09:00)。指定時は非公開で投稿される')
ap.add_argument('--no-thumbnail', action='store_true')
ap.add_argument('--no-captions', action='store_true')
ap.add_argument('--dry-run', action='store_true')
args = ap.parse_args()

with open(args.meta, encoding='utf-8') as f:
    meta = json.load(f)
video_path = os.path.join(UPLOAD, meta['file'])
if not os.path.exists(video_path):
    sys.exit(f'動画が見つかりません: {video_path}(先に ./build.sh を実行してください)')

privacy = args.privacy or meta.get('privacyStatus', 'private')
if args.publish_at:
    privacy = 'private'
body = {
    'snippet': {
        'title': meta['title'],
        'description': meta['description'],
        'tags': meta.get('tags', []),
        'categoryId': meta.get('categoryId', '19'),
        'defaultLanguage': meta.get('defaultLanguage', 'ja'),
        'defaultAudioLanguage': meta.get('defaultAudioLanguage', 'ja'),
    },
    'status': {
        'privacyStatus': privacy,
        'selfDeclaredMadeForKids': bool(meta.get('madeForKids', False)),
    },
}
if args.publish_at:
    body['status']['publishAt'] = args.publish_at

# 事前チェック(YouTube の制限)
assert len(meta['title']) <= 100, 'タイトルは100文字以内'
assert len(meta['description']) <= 5000, '説明文は5000文字以内'
assert len(','.join(f'"{t}"' if ' ' in t else t for t in meta.get('tags', []))) <= 500, 'タグは合計500文字以内'
assert '<' not in meta['title'] and '>' not in meta['title'], 'タイトルに < > は使えません'

print('動画      :', video_path, f'({os.path.getsize(video_path) / 1e6:.1f} MB)')
print('タイトル  :', meta['title'], f'({len(meta["title"])}文字)')
print('公開設定  :', privacy + (f'(公開予約 {args.publish_at})' if args.publish_at else ''))
print('カテゴリ  :', body['snippet']['categoryId'], '/ 子ども向け:', body['status']['selfDeclaredMadeForKids'])
print('タグ      :', ', '.join(meta.get('tags', [])))
if args.dry_run:
    print('\n--dry-run のため送信しません')
    sys.exit(0)

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

creds = None
if os.path.exists(args.token):
    creds = Credentials.from_authorized_user_file(args.token, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not os.path.exists(args.client_secret):
            sys.exit(f'client_secret.json が見つかりません: {args.client_secret}')
        creds = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES).run_local_server(port=0)
    with open(args.token, 'w') as f:
        f.write(creds.to_json())
yt = build('youtube', 'v3', credentials=creds)

# 1. 動画(再開可能アップロード)
media = MediaFileUpload(video_path, mimetype='video/mp4', chunksize=8 * 1024 * 1024, resumable=True)
req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
resp = None
while resp is None:
    try:
        status, resp = req.next_chunk()
        if status:
            print(f'  アップロード中 {int(status.progress() * 100)}%')
    except HttpError as e:
        if e.resp.status in (500, 502, 503, 504):
            print('  一時エラー、再試行:', e.resp.status); time.sleep(5)
        else:
            raise
video_id = resp['id']
print('投稿完了  : https://youtube.com/shorts/' + video_id)

# 2. サムネイル(チャンネルの電話番号確認が済んでいる必要あり)
if not args.no_thumbnail and meta.get('thumbnail'):
    try:
        yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(os.path.join(UPLOAD, meta['thumbnail']))).execute()
        print('サムネイル: 設定しました')
    except HttpError as e:
        print('サムネイル: 設定できませんでした(チャンネルの確認が必要な場合があります):', e)

# 3. 字幕
if not args.no_captions:
    for lang, srt in meta.get('captions', {}).items():
        try:
            yt.captions().insert(part='snippet', body={'snippet': {'videoId': video_id, 'language': lang, 'name': '日本語', 'isDraft': False}},
                                 media_body=MediaFileUpload(os.path.join(UPLOAD, srt), mimetype='application/octet-stream')).execute()
            print(f'字幕({lang}): 追加しました')
        except HttpError as e:
            print(f'字幕({lang}): 追加できませんでした:', e)

if meta.get('pinnedComment'):
    print('\n固定コメント(API では固定できないため、公開後に YouTube Studio で手動投稿→固定してください):')
    print(meta['pinnedComment'])
print('\n確認・公開: https://studio.youtube.com/video/' + video_id + '/edit')
