"""YouTube Data API v3 で動画をアップロードする（youtube_meta.json の内容を使用）。

準備（初回のみ）:
  1. Google Cloud Console でプロジェクトを作り「YouTube Data API v3」を有効化
  2. OAuth 2.0 クライアント ID（デスクトップ アプリ）を作成し client_secret.json をこのフォルダに保存
  3. pip install google-api-python-client google-auth-oauthlib
実行:
  python upload_youtube.py            # 非公開（private）でアップロードし、サムネイルと字幕も設定
  python upload_youtube.py --public   # 公開で投稿
ブラウザが開いて Google アカウントの認可を求めるので、投稿先チャンネルのアカウントで許可する。
"""
import argparse
import json
import pathlib

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

HERE = pathlib.Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", action="store_true", help="privacyStatus を public にする")
    ap.add_argument("--meta", default=str(HERE / "youtube_meta.json"))
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    args = ap.parse_args()

    meta = json.loads(pathlib.Path(args.meta).read_text(encoding="utf-8"))
    status = dict(meta["status"])
    if args.public:
        status["privacyStatus"] = "public"

    creds = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES).run_local_server(port=0)
    yt = build("youtube", "v3", credentials=creds)

    body = {"snippet": meta["snippet"], "status": status}
    media = MediaFileUpload(str(HERE / meta["file"]), chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        progress, resp = req.next_chunk()
        if progress:
            print(f"upload {int(progress.progress() * 100)}%")
    video_id = resp["id"]
    print("uploaded:", f"https://youtu.be/{video_id}")

    if meta.get("thumbnail") and (HERE / meta["thumbnail"]).exists():
        yt.thumbnails().set(videoId=video_id, media_body=str(HERE / meta["thumbnail"])).execute()
        print("thumbnail set")

    for lang, srt in meta.get("subtitles", {}).items():
        yt.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "language": lang, "name": "日本語", "isDraft": False}},
            media_body=MediaFileUpload(str(HERE / srt), mimetype="application/octet-stream"),
        ).execute()
        print("captions set:", lang)

    print("done. privacy:", status["privacyStatus"])


if __name__ == "__main__":
    main()
