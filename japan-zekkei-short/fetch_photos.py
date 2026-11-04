# -*- coding: utf-8 -*-
"""
Wikimedia Commons から、商用利用可能なフリー写真を自動取得する。

- 対象ライセンス: CC0 / パブリックドメイン / CC BY（SA・NC・ND は除外）
- photos/ に保存し、作者とライセンスを photos/credits.json と photos/CREDITS.md に記録する
- CC BY の写真は作者クレジットが必須（動画内の左下と、投稿の説明欄に記載）

必要なネットワーク許可: commons.wikimedia.org, upload.wikimedia.org
使い方: python3 fetch_photos.py [--force]
"""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import script as S

ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(ROOT, "photos")
API = "https://commons.wikimedia.org/w/api.php"
UA = "JapanZekkeiShortBuilder/1.0 (video build script; python-urllib)"

# 検索キーワード（上から順に試す）
QUERIES = {
    10: ["Tsunoshima Bridge", "角島大橋"],
    9: ["Takachiho Gorge Manai Falls", "高千穂峡 真名井の滝"],
    8: ["Shirogane Blue Pond Biei", "青い池 美瑛"],
    7: ["Takeda Castle sea of clouds", "竹田城跡 雲海"],
    6: ["Shiratani Unsuikyo Yakushima", "Jomon Sugi Yakushima"],
    5: ["Yonaha Maehama Beach Miyakojima", "与那覇前浜"],
    4: ["Shirakawa-go winter light up", "Shirakawa-go snow"],
    3: ["Kamikochi Kappa Bridge Hotaka", "Taisho Pond Kamikochi"],
    2: ["Yuki no Otani Tateyama", "雪の大谷"],
    1: ["Chureito Pagoda Mount Fuji", "Arakurayama Sengen Park Fuji"],
}

OK_LICENSE = re.compile(r"^(cc0|public domain|pd|cc by \d(\.\d)?|cc-by-\d(\.\d)?)", re.I)
NG_LICENSE = re.compile(r"\b(SA|NC|ND)\b", re.I)


def api(params):
    params.update(format="json", formatversion=2)
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def candidates(query):
    data = api(dict(action="query", generator="search", gsrsearch=f"{query} filetype:bitmap",
                    gsrnamespace=6, gsrlimit=30, prop="imageinfo",
                    iiprop="url|size|extmetadata", iiurlwidth=1800))
    pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = plain(meta.get("LicenseShortName", {}).get("value"))
        if not OK_LICENSE.match(lic) or NG_LICENSE.search(lic):
            continue
        if ii.get("width", 0) < 1200 or ii.get("height", 0) < 900:
            continue
        artist = plain(meta.get("Artist", {}).get("value")) or "Unknown"
        yield dict(title=p["title"], url=ii.get("thumburl") or ii["url"], page=ii.get("descriptionurl"),
                   license=lic, artist=artist[:60], w=ii["width"], h=ii["height"])


def main():
    force = "--force" in sys.argv
    os.makedirs(PHOTOS, exist_ok=True)
    cpath = os.path.join(PHOTOS, "credits.json")
    credits = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
    details = {}
    for sp in S.SPOTS:
        rank, fname, name = sp[0], sp[1], sp[2]
        dest = os.path.join(PHOTOS, fname)
        if os.path.exists(dest) and not force:
            print(f"[skip] {rank}位 {name}: 既にあります")
            continue
        found = None
        for q in QUERIES[rank]:
            for c in candidates(q):
                found = c
                break
            if found:
                break
        if not found:
            print(f"[NG] {rank}位 {name}: 条件に合う写真が見つかりませんでした（手動で photos/{fname} を置いてください）")
            continue
        req = urllib.request.Request(found["url"], headers={"User-Agent": UA})
        open(dest, "wb").write(urllib.request.urlopen(req, timeout=60).read())
        credits[fname] = f"{found['artist']} / {found['license']} (Wikimedia Commons)"
        details[fname] = found
        print(f"[OK] {rank}位 {name}: {found['title']} ({found['license']}, {found['artist']})")
    json.dump(credits, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(PHOTOS, "CREDITS.md"), "a", encoding="utf-8") as f:
        for fname, d in details.items():
            f.write(f"- {fname}: \"{d['title']}\" by {d['artist']}, {d['license']}, {d['page']}\n")
    print("クレジットは photos/credits.json と photos/CREDITS.md に保存しました。"
          "取得した写真が本当にその場所か、目で確認してから使ってください。")


if __name__ == "__main__":
    main()
