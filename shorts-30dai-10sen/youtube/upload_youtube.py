#!/usr/bin/env python3
"""Upload the short to YouTube with the YouTube Data API v3.

Setup (one time):
  1. Google Cloud Console で新規プロジェクト → 「YouTube Data API v3」を有効化
  2. 「OAuth 同意画面」を作成し、テストユーザーに自分の Google アカウントを追加
  3. 「認証情報」→「OAuth クライアント ID」→ 種類「デスクトップ アプリ」→ JSON をダウンロードし
     このフォルダに client_secret.json として保存
  4. pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Run:
  python3 upload_youtube.py                 # metadata.json の内容でアップロード（非公開）
  python3 upload_youtube.py --privacy public
  python3 upload_youtube.py --publish-at 2026-11-05T12:00:00+09:00   # 予約公開（privacy は private になる）
  python3 upload_youtube.py --no-thumbnail --no-captions
"""
import argparse, json, os, sys, time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]  # force-ssl: サムネイル・字幕の登録に必要

def get_service():
    token_path = os.path.join(HERE, "token.json")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret = os.path.join(HERE, "client_secret.json")
            if not os.path.exists(secret):
                sys.exit("client_secret.json がありません。ファイル先頭の Setup 手順を参照してください。")
            flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_video(yt, meta, privacy, publish_at):
    status = {"privacyStatus": privacy,
              "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
              "containsSyntheticMedia": bool(meta.get("contains_synthetic_media", False))}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "22"),
            "defaultLanguage": meta.get("default_language", "ja"),
            "defaultAudioLanguage": meta.get("default_audio_language", "ja"),
        },
        "status": status,
    }
    path = os.path.join(HERE, meta["video_file"])
    media = MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media,
                             notifySubscribers=bool(meta.get("notify_subscribers", True)))
    resp = None; retry = 0
    while resp is None:
        try:
            progress, resp = req.next_chunk()
            if progress: print(f"  upload {int(progress.progress()*100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retry < 5:
                retry += 1; wait = 2 ** retry; print(f"  retry in {wait}s ({e.resp.status})"); time.sleep(wait)
            else:
                raise
    return resp["id"]

def set_thumbnail(yt, video_id, path):
    yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(path, mimetype="image/png")).execute()

def add_captions(yt, video_id, path, lang, name):
    body = {"snippet": {"videoId": video_id, "language": lang, "name": name, "isDraft": False}}
    yt.captions().insert(part="snippet", body=body, media_body=MediaFileUpload(path, mimetype="application/octet-stream")).execute()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", default=os.path.join(HERE, "metadata.json"))
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"], default=None)
    ap.add_argument("--publish-at", default=None, help="RFC3339 (例 2026-11-05T12:00:00+09:00)。予約公開")
    ap.add_argument("--no-thumbnail", action="store_true")
    ap.add_argument("--no-captions", action="store_true")
    a = ap.parse_args()
    meta = json.load(open(a.metadata, encoding="utf-8"))
    privacy = a.privacy or meta.get("privacy_status", "private")
    yt = get_service()
    print("uploading:", meta["title"])
    vid = upload_video(yt, meta, privacy, a.publish_at)
    print("video id:", vid, "->", f"https://youtube.com/shorts/{vid}")
    if not a.no_thumbnail and meta.get("thumbnail_file"):
        try:
            set_thumbnail(yt, vid, os.path.join(HERE, meta["thumbnail_file"])); print("thumbnail set")
        except HttpError as e:
            print("thumbnail skipped:", e)  # カスタムサムネイルは電話番号認証済みチャンネルのみ
    if not a.no_captions and meta.get("captions_file"):
        add_captions(yt, vid, os.path.join(HERE, meta["captions_file"]), meta.get("captions_language", "ja"), meta.get("captions_name", "日本語"))
        print("captions added")
    print("done. YouTube Studio で内容を確認してから公開してください。")

if __name__ == "__main__":
    main()
