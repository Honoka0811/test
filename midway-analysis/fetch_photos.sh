#!/usr/bin/env bash
# Wikimedia Commons から写真を取得して photos/<scene id>.jpg に置く。
# 使い方: ./fetch_photos.sh photos/urls.txt   (1行 = "<scene id> <Commons の File:名 または 直接URL>")
# 例:      launch File:SBD-3 Dauntless bombers of VS-8 over the burning Japanese cruiser Mikuma on 6 June 1942.jpg
# ※ 制作環境では commons.wikimedia.org / upload.wikimedia.org へのアクセスが許可されていなかったため未実行。
set -euo pipefail
cd "$(dirname "$0")"
LIST=${1:-photos/urls.txt}
while read -r id src; do
  [ -z "$id" ] && continue; case "$id" in \#*) continue;; esac
  if [[ "$src" == http* ]]; then url="$src"
  else
    name=$(python3 -c "import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1].replace('File:','').replace(' ','_')))" "$src")
    url="https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${name}&width=1920"
  fi
  echo "$id <- $url"
  curl -sSL -A "midway-video-build/1.0" -o "photos/$id.jpg" "$url"
done < "$LIST"
echo "done. 次に node capture.js を再実行してください。"
