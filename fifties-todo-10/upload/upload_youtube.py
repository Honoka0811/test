#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube Data API v3 で動画・サムネイル・字幕をまとめて投稿する。

準備(初回のみ):
  1. https://console.cloud.google.com/ でプロジェクトを作り、「YouTube Data API v3」を有効化
  2. 「APIとサービス」→「認証情報」→「OAuth クライアント ID」→ 種類「デスクトップ アプリ」で作成
     (OAuth 同意画面が未設定なら先に作成し、テストユーザーに自分の Google アカウントを追加)
  3. ダウンロードした JSON を client_secret.json としてこのディレクトリに置く
  4. pip install google-api-python-client google-auth-oauthlib

使い方:
  python3 upload_youtube.py                    # youtube_metadata.json の内容で投稿(既定は限定公開)
  python3 upload_youtube.py --privacy public   # 公開で投稿
  python3 upload_youtube.py --dry-run          # 送信内容を表示するだけ
  python3 upload_youtube.py --no-thumbnail --no-caption

初回はブラウザが開いて Google アカウントの認可を求められ、token.json に保存されます。
API の 1 日あたりの割り当て(既定 10,000 ユニット)のうち、動画 1 本の投稿で約 1,600 ユニット、
サムネイルと字幕でそれぞれ約 50 ユニット使います。
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']
CLIENT_SECRET = os.path.join(HERE, 'client_secret.json')
TOKEN = os.path.join(HERE, 'token.json')


def load_meta(path):
    with open(path, encoding='utf-8') as f:
        meta = json.load(f)
    # YouTube の制限を事前チェック
    assert len(meta['title']) <= 100, 'タイトルは 100 文字以内'
    assert '<' not in meta['title'] and '>' not in meta['title'], 'タイトルに < > は使えない'
    assert len(meta['description']) <= 5000, '説明文は 5000 文字以内'
    assert len(','.join(meta['tags'])) <= 500, 'タグは合計 500 文字以内'
    for key in ('video_file', 'thumbnail_file', 'caption_file'):
        p = os.path.join(HERE, meta[key])
        assert os.path.exists(p), f'{meta[key]} が見つかりません'
    return meta


def get_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET):
                sys.exit(f'client_secret.json がありません: {CLIENT_SECRET}\n(冒頭のコメントの手順で作成してください)')
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN, 'w') as f:
            f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)


def upload_video(yt, meta, privacy):
    from googleapiclient.http import MediaFileUpload
    body = {
        'snippet': {
            'title': meta['title'],
            'description': meta['description'],
            'tags': meta['tags'],
            'categoryId': meta['category_id'],
            'defaultLanguage': meta['default_language'],
            'defaultAudioLanguage': meta['default_audio_language'],
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': meta['made_for_kids'],
            'containsSyntheticMedia': meta.get('contains_synthetic_media', False),
        },
    }
    media = MediaFileUpload(os.path.join(HERE, meta['video_file']), mimetype='video/mp4', chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    resp = None
    retry = 0
    while resp is None:
        try:
            status, resp = req.next_chunk()
            if status:
                print(f'  upload {int(status.progress() * 100)}%')
        except Exception as e:  # ネットワーク系は指数バックオフで再試行
            retry += 1
            if retry > 5:
                raise
            wait = 2 ** retry
            print(f'  retry {retry} after {wait}s: {e}')
            time.sleep(wait)
    return resp['id']


def set_thumbnail(yt, video_id, path):
    from googleapiclient.http import MediaFileUpload
    yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(path, mimetype='image/jpeg')).execute()


def upload_caption(yt, video_id, path, lang, name):
    from googleapiclient.http import MediaFileUpload
    yt.captions().insert(
        part='snippet',
        body={'snippet': {'videoId': video_id, 'language': lang, 'name': name, 'isDraft': False}},
        media_body=MediaFileUpload(path, mimetype='application/octet-stream'),
    ).execute()


def main():
    ap = argparse.ArgumentParser(description='YouTube に動画・サムネイル・字幕を投稿する')
    ap.add_argument('--meta', default=os.path.join(HERE, 'youtube_metadata.json'))
    ap.add_argument('--privacy', choices=['private', 'unlisted', 'public'], help='公開設定(既定は JSON の privacy_status)')
    ap.add_argument('--no-thumbnail', action='store_true')
    ap.add_argument('--no-caption', action='store_true')
    ap.add_argument('--dry-run', action='store_true', help='送信内容を表示するだけ')
    args = ap.parse_args()

    meta = load_meta(args.meta)
    privacy = args.privacy or meta['privacy_status']
    print('title      :', meta['title'])
    print('privacy    :', privacy)
    print('category   :', meta['category_id'], ' lang:', meta['default_language'], ' kids:', meta['made_for_kids'])
    print('tags       :', ', '.join(meta['tags']))
    print('video      :', meta['video_file'], f"({os.path.getsize(os.path.join(HERE, meta['video_file'])) / 1e6:.1f} MB)")
    print('thumbnail  :', 'skip' if args.no_thumbnail else meta['thumbnail_file'])
    print('caption    :', 'skip' if args.no_caption else f"{meta['caption_file']} ({meta['caption_language']})")
    print('description:\n' + '\n'.join('  ' + l for l in meta['description'].splitlines()))
    if args.dry_run:
        print('\n--dry-run: 送信しません')
        return

    yt = get_service()
    print('\nuploading video…')
    video_id = upload_video(yt, meta, privacy)
    print('video id:', video_id, ' url: https://youtu.be/' + video_id)
    if not args.no_thumbnail:
        try:
            set_thumbnail(yt, video_id, os.path.join(HERE, meta['thumbnail_file']))
            print('thumbnail: ok')
        except Exception as e:
            print('thumbnail: failed (チャンネルの電話番号確認が未済だとカスタムサムネイルは拒否されます):', e)
    if not args.no_caption:
        try:
            upload_caption(yt, video_id, os.path.join(HERE, meta['caption_file']), meta['caption_language'], meta['caption_name'])
            print('caption: ok')
        except Exception as e:
            print('caption: failed:', e)
    print('\n完了。YouTube Studio で処理完了後に再生確認し、必要なら公開設定を変更してください:')
    print(f'https://studio.youtube.com/video/{video_id}/edit')


if __name__ == '__main__':
    main()
