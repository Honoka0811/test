#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube Data API v3 で動画をアップロードし、サムネイルと字幕も設定する。

準備(初回のみ):
  1. https://console.cloud.google.com/ でプロジェクトを作り「YouTube Data API v3」を有効化
  2. 「認証情報」→「OAuth クライアント ID」→ 種類は「デスクトップ アプリ」→ JSON をダウンロードして
     このディレクトリに client_secret.json として置く(OAuth 同意画面のテストユーザーに自分の Google アカウントを追加)
  3. pip install google-api-python-client google-auth-oauthlib

使い方:
  python3 upload_youtube.py                 # youtube_metadata.json の内容で非公開アップロード
  python3 upload_youtube.py --dry-run       # ファイルとメタデータの検証だけ行う(認証不要)
  python3 upload_youtube.py --privacy unlisted
  python3 upload_youtube.py --publish-at 2026-11-05T21:00:00+09:00   # 予約公開(非公開でアップし指定時刻に公開)

初回は既定ブラウザが開くので Google アカウントでログインして許可する。トークンは token.json に保存される。
注意: Google の審査を受けていない API プロジェクトからアップロードした動画は「非公開」に固定されます。
     公開にする場合は YouTube Studio で公開設定を変更してください(スクリプトは既定で非公開のままアップロードします)。
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

def load_meta(path):
    m = json.load(open(path, encoding='utf-8'))
    problems = []
    if len(m['title']) > 100: problems.append(f"タイトルが100文字を超えています({len(m['title'])})")
    if '<' in m['title'] or '>' in m['title']: problems.append('タイトルに < > は使えません')
    if len(m['description']) > 5000: problems.append(f"説明文が5000文字を超えています({len(m['description'])})")
    tags_len = sum(len(t) + (2 if ' ' in t else 0) for t in m['tags']) + max(0, len(m['tags']) - 1)
    if tags_len > 500: problems.append(f'タグの合計が500文字を超えています({tags_len})')
    for key in ('video', 'thumbnail'):
        p = os.path.join(HERE, m[key])
        if not os.path.exists(p): problems.append(f'{key} が見つかりません: {p}')
    if m.get('captions') and not os.path.exists(os.path.join(HERE, m['captions']['file'])):
        problems.append('字幕ファイルが見つかりません: ' + m['captions']['file'])
    th = os.path.join(HERE, m['thumbnail'])
    if os.path.exists(th) and os.path.getsize(th) > 2 * 1024 * 1024: problems.append('サムネイルが2MBを超えています')
    return m, problems

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--meta', default=os.path.join(HERE, 'youtube_metadata.json'))
    ap.add_argument('--client-secret', default=os.path.join(HERE, 'client_secret.json'))
    ap.add_argument('--token', default=os.path.join(HERE, 'token.json'))
    ap.add_argument('--privacy', choices=['private', 'unlisted', 'public'], help='youtube_metadata.json の privacyStatus を上書き')
    ap.add_argument('--publish-at', help='予約公開日時(ISO 8601, 例 2026-11-05T21:00:00+09:00)。指定時は非公開でアップロード')
    ap.add_argument('--dry-run', action='store_true', help='検証のみ(アップロードしない)')
    ap.add_argument('--no-thumbnail', action='store_true'); ap.add_argument('--no-captions', action='store_true')
    a = ap.parse_args()

    meta, problems = load_meta(a.meta)
    print('タイトル :', meta['title'], f"({len(meta['title'])}文字)")
    print('動画     :', meta['video']); print('サムネ   :', meta['thumbnail']); print('字幕     :', meta.get('captions', {}).get('file'))
    privacy = a.privacy or meta.get('privacyStatus', 'private')
    if a.publish_at: privacy = 'private'
    print('公開設定 :', privacy + (f'(予約公開 {a.publish_at})' if a.publish_at else ''))
    if problems:
        print('\n問題があります:'); [print(' -', p) for p in problems]; sys.exit(1)
    print('検証 OK')
    if a.dry_run: return

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    creds = None
    if os.path.exists(a.token):
        creds = Credentials.from_authorized_user_file(a.token, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(a.client_secret):
                sys.exit(f'client_secret.json がありません: {a.client_secret}\n(Google Cloud Console で OAuth クライアント ID(デスクトップ)を作成して配置してください)')
            creds = InstalledAppFlow.from_client_secrets_file(a.client_secret, SCOPES).run_local_server(port=0)
        open(a.token, 'w').write(creds.to_json())
    yt = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {'title': meta['title'], 'description': meta['description'], 'tags': meta['tags'],
                    'categoryId': meta.get('categoryId', '22'), 'defaultLanguage': meta.get('defaultLanguage', 'ja'),
                    'defaultAudioLanguage': meta.get('defaultAudioLanguage', 'ja')},
        'status': {'privacyStatus': privacy, 'selfDeclaredMadeForKids': bool(meta.get('selfDeclaredMadeForKids', False))},
    }
    if a.publish_at: body['status']['publishAt'] = a.publish_at
    media = MediaFileUpload(os.path.join(HERE, meta['video']), mimetype='video/mp4', chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    resp, tries = None, 0
    while resp is None:
        try:
            status, resp = req.next_chunk()
            if status: print(f'\rアップロード中 {int(status.progress() * 100)}%', end='', flush=True)
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tries < 5:
                tries += 1; wait = 2 ** tries; print(f'\n一時エラー {e.resp.status}、{wait}秒後に再試行'); time.sleep(wait)
            else: raise
    vid = resp['id']
    print(f'\nアップロード完了: https://youtu.be/{vid}')

    if not a.no_thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(os.path.join(HERE, meta['thumbnail']))).execute()
            print('サムネイル設定 OK(ショートのフィードでは動画内のフレームが使われる場合があります)')
        except HttpError as e:
            print('サムネイル設定に失敗(電話番号認証済みチャンネルが必要です):', e)
    if not a.no_captions and meta.get('captions'):
        c = meta['captions']
        yt.captions().insert(part='snippet', body={'snippet': {'videoId': vid, 'language': c['language'], 'name': c.get('name', ''), 'isDraft': False}},
                             media_body=MediaFileUpload(os.path.join(HERE, c['file']), mimetype='application/octet-stream')).execute()
        print('字幕アップロード OK')
    print('YouTube Studio で確認: https://studio.youtube.com/video/' + vid + '/edit')

if __name__ == '__main__':
    main()
