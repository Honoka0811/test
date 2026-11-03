# -*- coding: utf-8 -*-
"""YouTube Data API v3 で upload/ の動画を投稿する。
使い方:
  python3 youtube_upload.py --check                 # ファイルとメタデータの検証だけ(API には接続しない)
  python3 youtube_upload.py                         # 投稿(初回はブラウザで Google アカウントの認可が必要)
  python3 youtube_upload.py --privacy public        # 公開設定を上書き(private / unlisted / public)
  python3 youtube_upload.py --publish-at 2026-11-05T19:00:00+09:00   # 予約公開(privacy は自動で private)
事前準備:
  1. Google Cloud Console でプロジェクトを作り「YouTube Data API v3」を有効化
  2. OAuth クライアント ID(種類: デスクトップアプリ)を作成し、JSON を upload/client_secret.json として保存
  3. pip install google-api-python-client google-auth-oauthlib
認可トークンは upload/token.json に保存され、2回目以降はブラウザ認可なしで投稿できる(どちらも .gitignore 済み)。
"""
import argparse, json, os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
UP = os.path.join(HERE, 'upload')
META = os.path.join(UP, 'metadata.json')
SECRET = os.path.join(UP, 'client_secret.json')
TOKEN = os.path.join(UP, 'token.json')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

def load_meta():
    with open(META, encoding='utf-8') as f:
        return json.load(f)

def check(meta):
    """ショート動画の要件とメタデータを検証する"""
    errors = []
    video = os.path.join(UP, meta['video'])
    if not os.path.exists(video):
        errors.append(f'動画がありません: {video}')
    else:
        p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=width,height,codec_name:format=duration', '-of', 'json', video], capture_output=True, text=True)
        info = json.loads(p.stdout); st = info['streams'][0]; dur = float(info['format']['duration'])
        w, h = int(st['width']), int(st['height'])
        if h <= w: errors.append(f'縦型(9:16)ではありません: {w}x{h}')
        if dur > 180: errors.append(f'ショート動画は 3 分以内です: {dur:.1f}s')
        if st['codec_name'] != 'h264': errors.append(f'映像コーデックが h264 ではありません: {st["codec_name"]}')
        print(f'動画: {w}x{h} {st["codec_name"]} {dur:.1f}s  {os.path.getsize(video) / 1e6:.1f}MB')
    if len(meta['title']) > 100: errors.append(f'タイトルは 100 文字以内です: {len(meta["title"])}')
    if any(c in meta['title'] for c in '<>'): errors.append('タイトルに < > は使えません')
    if len(meta['description']) > 5000: errors.append('説明文は 5000 文字以内です')
    if '#shorts' not in (meta['title'] + meta['description']).lower(): errors.append('タイトルか説明文に #Shorts を入れてください')
    if 'VOICEVOX:四国めたん' not in meta['description']: errors.append('説明文に「VOICEVOX:四国めたん」のクレジットが必要です(利用規約)')
    tags = meta.get('tags', [])
    if sum(len(t) + 2 for t in tags) > 500: errors.append('タグの合計は 500 文字以内です')
    if meta.get('privacyStatus') not in ('private', 'unlisted', 'public'): errors.append('privacyStatus が不正です')
    for c in meta.get('captions', []):
        if not os.path.exists(os.path.join(UP, c['file'])): errors.append(f'字幕がありません: {c["file"]}')
    th = meta.get('thumbnail')
    if th and not os.path.exists(os.path.join(UP, th)): errors.append(f'サムネイルがありません: {th}')
    if th and os.path.getsize(os.path.join(UP, th)) > 2 * 1024 * 1024: errors.append('サムネイルは 2MB 以内です')
    print(f'タイトル({len(meta["title"])}文字): {meta["title"]}')
    print(f'説明文: {len(meta["description"])}文字 / タグ: {len(tags)}個 / 公開設定: {meta["privacyStatus"]}')
    for e in errors: print('NG:', e)
    return not errors

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
            if not os.path.exists(SECRET):
                sys.exit(f'OAuth クライアントの JSON がありません: {SECRET}\n(Google Cloud Console → 認証情報 → OAuth クライアント ID「デスクトップアプリ」を作成して保存してください)')
            flow = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
        with open(TOKEN, 'w') as f: f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload(meta, privacy=None, publish_at=None):
    from googleapiclient.http import MediaFileUpload
    yt = get_service()
    status = {'privacyStatus': privacy or meta['privacyStatus'], 'selfDeclaredMadeForKids': meta.get('selfDeclaredMadeForKids', False)}
    if publish_at:
        status['privacyStatus'] = 'private'; status['publishAt'] = publish_at
    body = {
        'snippet': {'title': meta['title'], 'description': meta['description'], 'tags': meta.get('tags', []),
                    'categoryId': meta.get('categoryId', '22'), 'defaultLanguage': meta.get('defaultLanguage', 'ja'),
                    'defaultAudioLanguage': meta.get('defaultAudioLanguage', 'ja')},
        'status': status,
    }
    media = MediaFileUpload(os.path.join(UP, meta['video']), mimetype='video/mp4', chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st: print(f'  アップロード中 {int(st.progress() * 100)}%')
    vid = resp['id']
    print('投稿しました:', f'https://youtube.com/shorts/{vid}')
    if meta.get('thumbnail'):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(os.path.join(UP, meta['thumbnail']))).execute()
            print('サムネイルを設定しました(ショートでは表示されない場所もあります)')
        except Exception as e:  # noqa
            print('サムネイル設定はスキップ:', e)
    for c in meta.get('captions', []):
        yt.captions().insert(part='snippet', body={'snippet': {'videoId': vid, 'language': c['language'], 'name': c['name']}},
                             media_body=MediaFileUpload(os.path.join(UP, c['file']), mimetype='application/octet-stream')).execute()
        print('字幕を追加しました:', c['name'])
    return vid

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='検証のみ')
    ap.add_argument('--privacy', choices=['private', 'unlisted', 'public'])
    ap.add_argument('--publish-at', help='予約公開日時(RFC3339, 例 2026-11-05T19:00:00+09:00)')
    a = ap.parse_args()
    meta = load_meta()
    ok = check(meta)
    if a.check or not ok:
        sys.exit(0 if ok else 1)
    upload(meta, a.privacy, a.publish_at)
