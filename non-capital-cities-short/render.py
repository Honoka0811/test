"""縦型ショート動画（1080x1920, 30fps）のフレームを描画して ffmpeg で書き出す。
usage: python3 render.py <data_dir> <audio_dir> <out.mp4>
  data_dir: japan.geojson, MPLUSRounded1c-*.ttf
  audio_dir: n00.wav.. durations.json bgm.wav
"""
import json
import math
import os
import subprocess
import sys
import wave
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SCENES  # noqa: E402

DATA, AUDIO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS, SS = 1080, 1920, 30, 2
MAP_TOP, MAP_H = 300, 1010
K = math.cos(math.radians(36))
GAP = 0.55          # シーン末尾の余白（秒）
LEAD = 0.25         # ナレーション開始までの間
END_CARD = 3.2      # 最後のまとめカード

# ---------- 色 ----------
NAVY = (27, 38, 72)
SEA_TOP, SEA_BOT = (178, 219, 240), (140, 196, 228)
LAND = (250, 247, 238)
BORDER = (196, 186, 166)
COAST = (120, 150, 170)
HI = (255, 176, 59)
HI_BORDER = (214, 120, 20)
RED = (232, 64, 58)
GRAY = (90, 98, 112)
GOLD, SILVER, BRONZE = (226, 160, 0), (140, 152, 168), (205, 127, 60)
WHITE = (255, 255, 255)
INK = (30, 34, 44)


@lru_cache(None)
def font(size, bold=True):
    name = "MPLUSRounded1c-ExtraBold.ttf" if bold else "MPLUSRounded1c-Bold.ttf"
    return ImageFont.truetype(os.path.join(DATA, name), int(size * SS))


# ---------- 地図データ ----------
def load_geo():
    gj = json.load(open(os.path.join(DATA, "japan.geojson")))
    levels = {}
    for tol, min_area in ((0.02, 0.004), (0.006, 0.0006), (0.0015, 0.0)):
        prefs = []
        for f in gj["features"]:
            g = shape(f["geometry"]).simplify(tol, preserve_topology=True)
            polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
            rings = []
            for p in polys:
                if p.area < min_area:
                    continue
                a = np.asarray(p.exterior.coords)
                a = np.stack([a[:, 0] * K, a[:, 1]], 1)
                rings.append((a, a.min(0), a.max(0)))
            prefs.append((f["properties"]["nam_ja"], rings))
        levels[tol] = prefs
    return levels


GEO = load_geo()


# ---------- カメラ ----------
def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def cam_for(s):
    if s["kind"] == "title":
        return (137.6, 36.6, 17.0)
    if s["kind"] == "outro":
        return (139.42, 35.48, 1.35)
    cx = (s["lon"] + s["cap_lon"]) / 2
    cy = (s["lat"] + s["cap_lat"]) / 2
    dx = abs(s["lon"] - s["cap_lon"])
    dy = abs(s["lat"] - s["cap_lat"]) / K * (W / MAP_H)
    span = max(1.25, 2.2 * max(dx, dy) + 0.5)
    return (cx, cy - span * 0.06, span)


def fly(c0, c1, e, dist_bump=True):
    ls = math.log(c0[2]) * (1 - e) + math.log(c1[2]) * e
    d = math.hypot(c1[0] - c0[0], c1[1] - c0[1])
    bump = 1 + (min(d / max(c0[2], c1[2]), 1.5) * 1.4 if dist_bump else 0) * math.sin(math.pi * e)
    return (c0[0] + (c1[0] - c0[0]) * e, c0[1] + (c1[1] - c0[1]) * e, math.exp(ls) * bump)


def to_px(cam, lon, lat):
    cx, cy, span = cam
    sc = W / (span * K)
    return (W / 2 + (lon * K - cx * K) * sc, MAP_TOP + MAP_H / 2 - (lat - cy) * sc)


@lru_cache(maxsize=8)
def render_map(cam, highlight):
    cx, cy, span = cam
    tol = 0.02 if span > 6 else (0.006 if span > 2.2 else 0.0015)
    sc = W / (span * K) * SS
    img = Image.new("RGB", (W * SS, MAP_H * SS))
    # 海のグラデーション
    grad = np.linspace(0, 1, MAP_H * SS)[:, None, None]
    sea = (np.array(SEA_TOP) * (1 - grad) + np.array(SEA_BOT) * grad).astype(np.uint8)
    img = Image.fromarray(np.repeat(sea, W * SS, 1))
    d = ImageDraw.Draw(img)
    hx = W * SS / 2 / sc
    hy = MAP_H * SS / 2 / sc
    x0, x1, y0, y1 = cx * K - hx, cx * K + hx, cy - hy, cy + hy
    lw_b = max(1, int(1.6 * SS * min(1.0, 3 / span) + 1))
    order = sorted(GEO[tol], key=lambda p: p[0] in highlight)
    for name, rings in order:
        on = name in highlight
        for a, mn, mx in rings:
            if mx[0] < x0 or mn[0] > x1 or mx[1] < y0 or mn[1] > y1:
                continue
            px = (a[:, 0] - cx * K) * sc + W * SS / 2
            py = MAP_H * SS / 2 - (a[:, 1] - cy) * sc
            pts = list(zip(px.tolist(), py.tolist()))
            if len(pts) < 3:
                continue
            d.polygon(pts, fill=HI if on else LAND)
            d.line(pts + [pts[0]], fill=HI_BORDER if on else BORDER,
                   width=lw_b * (2 if on else 1), joint="curve")
    return img


IW, IH = 276, 320
INSET = [W - 24 - IW, MAP_TOP + 24, W - 24, MAP_TOP + 24 + IH]   # ミニ日本地図（位置はシーンごとに決定）
CORNERS = [(W - 24 - IW, MAP_TOP + 24), (24, MAP_TOP + 24), (24, 1220 - IH), (W - 24 - IW, 1220 - IH)]


def place_inset(cam, pts):
    best = max(CORNERS, key=lambda c: min(math.hypot(c[0] + IW / 2 - x, c[1] + IH / 2 - y) for x, y in pts))
    INSET[:] = [best[0], best[1], best[0] + IW, best[1] + IH]
INSET_CAM = (137.0, 37.6, 17.5)                          # (中心lon, 中心lat, 幅lon)


def inset_px(lon, lat):
    cx, cy, span = INSET_CAM
    w = INSET[2] - INSET[0]
    sc = w / (span * K)
    return (INSET[0] + w / 2 + (lon - cx) * K * sc, (INSET[1] + INSET[3]) / 2 - (lat - cy) * sc)


@lru_cache(None)
def inset_base():
    w, h = INSET[2] - INSET[0], INSET[3] - INSET[1]
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=S(22), fill=(255, 255, 255, 235),
                        outline=NAVY + (255,), width=S(4))
    for _, rings in GEO[0.02]:
        for a, _, _ in rings:
            pts = [((x / K * K - INSET_CAM[0] * K) * (w / (INSET_CAM[2] * K)) * SS + w * SS / 2,
                    h * SS / 2 - (y - INSET_CAM[1]) * (w / (INSET_CAM[2] * K)) * SS) for x, y in a]
            pts = [(x, y) for x, y in pts]
            if len(pts) >= 3:
                d.polygon(pts, fill=(205, 212, 224))
    return img


def draw_inset(img, d, cam, pref_pts):
    img.paste(inset_base(), (S(INSET[0]), S(INSET[1])), inset_base())
    for lon, lat, col in pref_pts:
        x, y = inset_px(lon, lat)
        d.ellipse([S(x - 9), S(y - 9), S(x + 9), S(y + 9)], fill=col, outline=WHITE, width=S(2))
    # 今見ている範囲
    cx, cy, span = cam
    hx = span / 2
    hy = span / 2 * MAP_H / W
    x0, y0 = inset_px(cx - hx, cy + hy)
    x1, y1 = inset_px(cx + hx, cy - hy)
    if x1 - x0 < INSET[2] - INSET[0] - 10:
        d.rectangle([S(max(x0, INSET[0])), S(max(y0, INSET[1])), S(min(x1, INSET[2])), S(min(y1, INSET[3]))],
                    outline=RED, width=S(4))
    text(d, ((INSET[0] + INSET[2]) / 2, INSET[3] - 26), "現在地", 24, NAVY)


# ---------- 描画ヘルパ ----------
def S(v):
    return int(round(v * SS))


def text(d, xy, s, size, fill, anchor="mm", bold=True, stroke=0, stroke_fill=WHITE, spacing=8):
    d.multiline_text((S(xy[0]), S(xy[1])), s, font=font(size, bold), fill=fill, anchor=anchor,
                     stroke_width=S(stroke), stroke_fill=stroke_fill, spacing=S(spacing), align="center")


def rrect(d, box, r, fill, outline=None, width=0):
    d.rounded_rectangle([S(box[0]), S(box[1]), S(box[2]), S(box[3])], radius=S(r), fill=fill,
                        outline=outline, width=S(width))


def pin(d, x, y, scale, color=RED, label=None):
    if scale <= 0:
        return
    r = 24 * scale
    h = 62 * scale
    d.ellipse([S(x - 16 * scale), S(y - 5 * scale), S(x + 16 * scale), S(y + 5 * scale)], fill=(0, 0, 0, 60))
    cy = y - h + r
    d.polygon([(S(x - r * 0.82), S(cy + r * 0.55)), (S(x + r * 0.82), S(cy + r * 0.55)), (S(x), S(y))], fill=color)
    d.ellipse([S(x - r), S(cy - r), S(x + r), S(cy + r)], fill=color, outline=WHITE, width=S(3))
    d.ellipse([S(x - r * 0.4), S(cy - r * 0.4), S(x + r * 0.4), S(cy + r * 0.4)], fill=WHITE)


def label_box(d, x, y, s, size, fg, bg, side, alpha=1.0):
    f = font(size)
    bb = d.multiline_textbbox((0, 0), s, font=f, spacing=S(4))
    tw, th = (bb[2] - bb[0]) / SS, (bb[3] - bb[1]) / SS
    pad = 12
    bw, bh = tw + pad * 2, th + pad * 1.6
    bx = x + 34 if side > 0 else x - 34 - bw
    bx = min(max(bx, 12), W - 12 - bw)
    by = min(max(y - bh / 2, MAP_TOP + 10), MAP_TOP + MAP_H - bh - 10)
    rrect(d, (bx, by, bx + bw, by + bh), 14, bg, outline=fg if bg == WHITE else None, width=3)
    d.multiline_text((S(bx + bw / 2), S(by + bh / 2)), s, font=f, fill=fg if bg == WHITE else WHITE,
                     anchor="mm", spacing=S(4), align="center")


def cap_marker(d, x, y, s):
    d.ellipse([S(x - 13), S(y - 13), S(x + 13), S(y + 13)], fill=WHITE, outline=GRAY, width=S(5))
    d.ellipse([S(x - 5), S(y - 5), S(x + 5), S(y + 5)], fill=GRAY)


def rank_color(r):
    return {1: GOLD, 2: SILVER, 3: BRONZE}.get(r, RED)


# ---------- タイムライン ----------
durs = json.load(open(os.path.join(AUDIO, "durations.json")))
starts, t = [], 0.0
for dd in durs:
    starts.append(t)
    t += LEAD + dd + GAP
END_START = t
TOTAL = t + END_CARD
NFRAMES = int(TOTAL * FPS)
CAMS = [cam_for(s) for s in SCENES]


def scene_at(tt):
    for i in range(len(SCENES) - 1, -1, -1):
        if tt >= starts[i]:
            return i
    return 0


def camera(i, lt):
    c1 = CAMS[i]
    if i == 0:
        z = 1 + 0.08 * (1 - ease(lt / 4))
        return (c1[0], c1[1], c1[2] * z)
    c0 = CAMS[i - 1]
    e = ease(lt / 1.0)
    if e >= 1:
        # ゆっくりズームイン
        z = 1 - 0.04 * ease((lt - 1.0) / 6)
        return (c1[0], c1[1], c1[2] * z)
    return fly(c0, c1, e)


def quant(cam):
    return (round(cam[0], 4), round(cam[1], 4), round(cam[2], 4))


def draw_header(d, s, lt):
    rrect(d, (0, -40, W, MAP_TOP + 6), 0, NAVY)
    text(d, (W / 2, 62), "県庁所在地じゃない大都市ランキング", 40, (255, 220, 120))
    if s["kind"] == "rank":
        pop = ease(lt / 0.35)
        sc = 0.6 + 0.4 * pop + 0.12 * math.sin(min(lt / 0.35, 1) * math.pi)
        r = s["rank"]
        col = rank_color(r)
        text(d, (W / 2, 190), f"第{r}位", 130 * sc, col, stroke=6 * sc, stroke_fill=NAVY)
    elif s["kind"] == "title":
        text(d, (W / 2, 190), "TOP 10", 140, WHITE, stroke=6, stroke_fill=NAVY)
    else:
        text(d, (W / 2, 190), "まとめ", 120, WHITE)


def draw_card(d, s, lt, cam):
    slide = ease(lt / 0.45)
    off = (1 - slide) * (W + 40)
    x0, y0, x1, y1 = 50 + off, 1240, W - 50 + off, 1560
    rrect(d, (x0 + 6, y0 + 10, x1 + 6, y1 + 10), 36, (0, 0, 0, 0) if False else (120, 140, 160))
    rrect(d, (x0, y0, x1, y1), 36, WHITE)
    if s["kind"] == "title":
        text(d, ((x0 + x1) / 2, y0 + 105), "人口は2020年国勢調査（概数）", 46, INK)
        text(d, ((x0 + x1) / 2, y0 + 190), "東京23区は「市」ではないので除外", 40, GRAY, bold=False)
        text(d, ((x0 + x1) / 2, y0 + 260), "10位から発表！", 46, RED)
        return
    if s["kind"] == "outro":
        text(d, ((x0 + x1) / 2, y0 + 70), "神奈川県の政令指定都市", 46, INK)
        rows = [("横浜市", "県庁所在地", GRAY), ("川崎市", "1位 154万人", GOLD), ("相模原市", "5位 73万人", RED)]
        for k, (a, b, c) in enumerate(rows):
            yy = y0 + 150 + k * 60
            text(d, (x0 + 290, yy), a, 44, INK, anchor="rm")
            text(d, (x0 + 330, yy), b, 44, c, anchor="lm")
        return
    col = rank_color(s["rank"])
    text(d, (x0 + 50, y0 + 62), s["pref"], 46, GRAY, anchor="lm")
    text(d, (x0 + 50, y0 + 150), s["city"], 108, INK, anchor="lm")
    cnt = s["pop"] * ease((lt - 0.4) / 0.9)
    v = round(cnt) if s["pop"] >= 1 else cnt
    text(d, (x1 - 50, y0 + 150), f"約{v:.0f}万人", 78, col, anchor="rm")
    # 人口バー（1位=川崎を基準）
    bx0, bx1, by = x0 + 50, x1 - 50, y0 + 250
    rrect(d, (bx0, by - 18, bx1, by + 18), 18, (236, 238, 242))
    frac = cnt / 153.8
    if frac > 0.02:
        rrect(d, (bx0, by - 18, bx0 + (bx1 - bx0) * frac, by + 18), 18, col)
    text(d, (bx1, by + 40), "バー：1位の川崎市を100%としたとき", 26, GRAY, anchor="rm", bold=False)


def draw_subtitle(d, s, lt, dur):
    if s["kind"] == "title":
        lines = ""
    elif s["kind"] == "rank":
        lines = s["text"].split("\n")[1]
    else:
        lines = s["text"]
    if not lines:
        return
    a = ease((lt - LEAD) / 0.25)
    if a <= 0:
        return
    size = 58 if "\n" not in lines else 54
    while size > 36:
        bb = d.multiline_textbbox((0, 0), lines, font=font(size), stroke_width=S(10), spacing=S(14))
        if (bb[2] - bb[0]) / SS <= W - 60:
            break
        size -= 2
    text(d, (W / 2, 1715), lines, size, INK, stroke=10, stroke_fill=WHITE, spacing=14)


def draw_title_overlay(d, lt):
    a = ease((lt - 0.15) / 0.5)
    sc = 0.7 + 0.3 * a
    y = MAP_TOP + MAP_H / 2 - 30
    rrect(d, (90, y - 190 * sc, W - 90, y + 190 * sc), 40, WHITE, outline=NAVY, width=8)
    text(d, (W / 2, y - 70 * sc), "県庁所在地じゃないのに", 64 * sc, INK)
    text(d, (W / 2, y + 50 * sc), "実は超デカい街", 108 * sc, RED, stroke=4, stroke_fill=WHITE)
    text(d, (W / 2, y + 140 * sc), "TOP10", 60 * sc, NAVY)


def draw_markers(d, s, lt, cam):
    arrive = 0.95  # カメラ到着後にピン
    p = (lt - arrive) / 0.35
    if p <= 0:
        return
    bounce = 1 if p >= 1 else (math.sin(p * math.pi * 0.5) * (1 + 0.25 * math.sin(p * math.pi)))
    if s["kind"] == "outro":
        items = [("川崎市", 139.703, 35.531, GOLD, "1位 川崎市", 1),
                 ("相模原市", 139.373, 35.571, RED, "5位 相模原市", -1)]
        yx, yy = to_px(cam, 139.638, 35.444)
        cap_marker(d, yx, yy, "")
        label_box(d, yx, yy + 50, "県庁所在地 横浜市", 30, GRAY, WHITE, 1)
        for _, lon, lat, c, lab, side in items:
            x, y = to_px(cam, lon, lat)
            pin(d, x, y, bounce, c)
            if p >= 0.6:
                label_box(d, x, y - 40, lab, 40, c, c, side)
        return
    cx, cy = to_px(cam, s["cap_lon"], s["cap_lat"])
    x, y = to_px(cam, s["lon"], s["lat"])
    side = 1 if x >= cx else -1
    if abs(x - cx) < 40:
        side = 1
    cap_lab = ("都庁所在地\n" if s["pref"] == "東京都" else "県庁所在地\n") + s["cap"]
    if s["pref"] == "大阪府":
        cap_lab = "府庁所在地\n" + s["cap"]
    if p > 0.3:
        cap_marker(d, cx, cy, s["cap"])
        label_box(d, cx, cy, cap_lab, 28, GRAY, WHITE, -side)
    # パルス
    if p >= 1:
        ph = ((lt - arrive - 0.35) % 1.4) / 1.4
        rr = 20 + 70 * ph
        col = (*rank_color(s["rank"]),)
        d.ellipse([S(x - rr), S(y - rr * 0.45), S(x + rr), S(y + rr * 0.45)],
                  outline=tuple(int(c * (1 - ph) + 255 * ph) for c in col), width=S(4))
    pin(d, x, y, bounce, rank_color(s["rank"]) if s["rank"] <= 3 else RED)
    if p >= 0.6:
        c = rank_color(s["rank"]) if s["rank"] <= 3 else RED
        label_box(d, x, y - 40, s["city"], 44, c, c, side)


def draw_end(d, lt):
    a = ease(lt / 0.4)
    rrect(d, (0, 0, W, H), 0, NAVY)
    text(d, (W / 2, 150), "県庁所在地じゃない大都市", 56, (255, 220, 120))
    text(d, (W / 2, 240), "TOP10 まとめ", 84, WHITE)
    ranks = sorted([s for s in SCENES if s["kind"] == "rank"], key=lambda s: s["rank"])
    for k, s in enumerate(ranks):
        yy = 380 + k * 128
        sh = ease((lt - 0.05 * k) / 0.35)
        off = (1 - sh) * 300
        rrect(d, (70 + off, yy - 52, W - 70 + off, yy + 52), 26, WHITE if s["rank"] > 3 else (255, 248, 225))
        col = rank_color(s["rank"])
        d.ellipse([S(100 + off), S(yy - 38), S(176 + off), S(yy + 38)], fill=col)
        text(d, (138 + off, yy + 2), str(s["rank"]), 44, WHITE)
        text(d, (205 + off, yy), s["city"], 52, INK, anchor="lm")
        text(d, (520 + off, yy), s["pref"], 34, GRAY, anchor="lm", bold=False)
        text(d, (W - 100 + off, yy), f"約{s['pop']:.0f}万人", 46, col if s["rank"] <= 3 else RED, anchor="rm")
    text(d, (W / 2, 1720), "人口：2020年国勢調査（概数）", 34, (200, 210, 230), bold=False)
    _ = a


def frame(fi):
    tt = fi / FPS
    if tt >= END_START:
        img = Image.new("RGB", (W * SS, H * SS), NAVY)
        d = ImageDraw.Draw(img, "RGBA")
        draw_end(d, tt - END_START)
    else:
        i = scene_at(tt)
        s = SCENES[i]
        lt = tt - starts[i]
        cam = quant(camera(i, lt))
        if s["kind"] == "rank":
            hl = (s["pref"],)
        elif s["kind"] == "outro":
            hl = ("神奈川県",)
        else:
            hl = ()
        # 遷移中は前シーンの県のハイライトを残さない（到着後に色付け）
        if i > 0 and lt < 0.9:
            hl = ()
        img = Image.new("RGB", (W * SS, H * SS), (244, 246, 250))
        img.paste(render_map(cam, hl), (0, MAP_TOP * SS))
        d = ImageDraw.Draw(img, "RGBA")
        if s["kind"] == "title":
            draw_title_overlay(d, lt)
        else:
            draw_markers(d, s, lt, cam)
            if s["kind"] == "rank":
                dots = [(s["lon"], s["lat"], rank_color(s["rank"]) if s["rank"] <= 3 else RED)]
            else:
                dots = [(139.703, 35.531, GOLD), (139.373, 35.571, RED)]
            final = CAMS[i]
            if s["kind"] == "rank":
                keys = [to_px(final, s["lon"], s["lat"]), to_px(final, s["cap_lon"], s["cap_lat"])]
            else:
                keys = [to_px(final, 139.703, 35.531), to_px(final, 139.373, 35.571), to_px(final, 139.638, 35.444)]
            # ラベル分の余裕として左右に少し広げる
            keys += [(x + dx, y) for x, y in keys for dx in (-150, 150)]
            place_inset(final, keys)
            draw_inset(img, d, cam, dots)
        draw_header(d, s, lt)
        # 地図下部の白い帯
        rrect(d, (0, MAP_TOP + MAP_H - 4, W, H + 40), 0, (244, 246, 250))
        draw_card(d, s, lt, cam)
        draw_subtitle(d, s, lt, durs[i])
    d = ImageDraw.Draw(img, "RGBA")
    text(d, (W - 30, H - 50), "VOICEVOX:四国めたん", 30, (150, 160, 175) if tt < END_START else (200, 210, 230),
         anchor="rm", bold=False)
    return img.resize((W, H), Image.LANCZOS).tobytes()


# ---------- 音声ミックス ----------
def read_wav(p):
    with wave.open(p) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    x = x.reshape(-1, ch)
    if ch == 1:
        x = np.repeat(x, 2, 1)
    assert sr == 48000, sr
    return x


def mix_audio(path):
    SR = 48000
    n = int(TOTAL * SR) + SR
    narr = np.zeros((n, 2), np.float32)
    for i in range(len(SCENES)):
        x = read_wav(os.path.join(AUDIO, f"n{i:02d}.wav"))
        a = int((starts[i] + LEAD) * SR)
        narr[a:a + len(x)] += x
    bgm = read_wav(os.path.join(AUDIO, "bgm.wav"))[:n]
    bgm = np.pad(bgm, ((0, n - len(bgm)), (0, 0)))
    # ナレーション中はBGMを下げる（簡易ダッキング）
    lvl = np.abs(narr).max(1)
    win = int(0.25 * SR)
    lvl = np.convolve(lvl > 0.02, np.ones(win) / win, "same")
    g = 0.30 - 0.17 * np.clip(lvl * 3, 0, 1)
    out = narr * 1.35 + bgm * g[:, None]
    out = out[: int(TOTAL * SR)]
    out /= max(1.0, np.abs(out).max() / 0.97)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[4] == "--preview":
        for sec in [float(v) for v in sys.argv[5].split(",")]:
            Image.frombytes("RGB", (W, H), frame(int(sec * FPS))).save(f"{OUT}_{sec:05.1f}.png")
        sys.exit()
    print(f"total {TOTAL:.1f}s, {NFRAMES} frames")
    mix = OUT + ".mix.wav"
    mix_audio(mix)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", mix, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(frame, range(NFRAMES), chunksize=12)):
            ff.stdin.write(buf)
            if k % 300 == 0:
                print(f"frame {k}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(mix)
    print("done", OUT)
