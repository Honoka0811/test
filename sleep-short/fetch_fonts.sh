#!/usr/bin/env bash
# Google Fonts から字幕・見出し用フォント(いずれも SIL Open Font License)を取得する
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts
get() {
  local url
  url=$(curl -sS "https://fonts.googleapis.com/css2?family=$1" | grep -o 'https://[^)]*\.ttf' | head -1)
  curl -sS -o "fonts/$2" "$url"
}
get 'Shippori+Mincho+B1:wght@800' ShipporiMinchoB1-ExtraBold.ttf
get 'Zen+Kaku+Gothic+New:wght@700' ZenKakuGothicNew-Bold.ttf
ls -la fonts
