"""Map-based version: camera flies to each city on a 1940-style map."""
import math, os, sys, subprocess, random, pickle
from multiprocessing import Pool
import numpy as np
import aggdraw
from PIL import Image, ImageDraw, ImageFilter
from render import (W, H, FPS, F_DELA, F_BLACK, F_BOLD, SCENES, TOTAL, S, REG, RANKS, SUBS, EXTRAS,
                    text_img, paste_c, paste_l, ease_out, ease_back, clamp, credit, subtitle, confetti)
from geo import merc_y
from timeline import HERE

MAP = pickle.load(open(os.path.join(HERE, "map.pkl"), "rb"))
BB = {k: [(p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()) for p in v] for k, v in MAP.items()}
LAYER_REG = {"chosen": "朝鮮", "taiwan": "台湾", "kanto": "関東州", "karafuto": "樺太", "nanyo": "南洋"}
REG_LAYER = {v: k for k, v in LAYER_REG.items()}
REG_LAYER["北方領土"] = "hoppo"

CITY = {10: (120.30, 22.63), 9: (120.21, 22.99), 8: (126.62, 37.46), 7: (128.60, 35.87), 6: (129.78, 41.80),
        5: (129.04, 35.10), 4: (125.75, 39.03), 3: (121.56, 25.04), 2: (121.60, 38.91), 1: (126.98, 37.57)}
EXTRA_PINS = {
    "kara": [("豊原", 142.73, 46.96)],
    "nanyo": [("コロール", 134.48, 7.34), ("ガラパン", 145.72, 15.21)],
    "hoppo": [("古釜布", 145.86, 44.02, "L"), ("紗那", 147.88, 45.24), ("斜古丹", 146.83, 43.87)],
}
OVER = (137.5, 33.0, 13.5, 680)

def city_cam(lon, lat, s, fy=700): return (lon, merc_y(lat), s, fy)
def cam_for(key):
    if key in ("hook",): return city_cam(138.5, 36.5, 46, 760)
    if key in ("title", "extra", "outro"): return OVER
    if key == "tease": return city_cam(125.0, 32.0, 26, 650)
    if key.startswith("r") and key[1:].isdigit():
        r = int(key[1:]); lon, lat = CITY[r]
        s = {10: 150, 9: 150, 3: 135, 2: 92}.get(r, 108)
        if r == 1: s = 125
        return city_cam(lon, lat, s)
    if key == "kara": return city_cam(142.7, 47.4, 92, 720)
    if key == "nanyo": return city_cam(140.0, 11.5, 44, 720)
    if key == "hoppo": return city_cam(146.4, 44.3, 150, 720)
    return OVER

def lerp(a, b, p): return a + (b - a) * p
def ease_io(x): x = clamp(x); return x * x * (3 - 2 * x)

def camera(t):
    idx = next((i for i, s in enumerate(SCENES) if s["start"] <= t < s["end"]), len(SCENES) - 1)
    sc = SCENES[idx]; lt = t - sc["start"]
    tgt = cam_for(sc["key"])
    if sc["key"] == "hook":
        p = ease_io(lt / (sc["end"] - sc["start"]))
        a = city_cam(138.5, 36.5, 46, 760)
        return (lerp(a[0], OVER[0], p), lerp(a[1], OVER[1], p), math.exp(lerp(math.log(a[2]), math.log(OVER[2]), p)), lerp(a[3], OVER[3], p))
    prev = cam_for(SCENES[idx - 1]["key"]) if idx > 0 else tgt
    if prev == tgt: cam = tgt
    else:
        p = ease_io(lt / 0.85)
        dist = math.hypot(tgt[0] - prev[0], tgt[1] - prev[1])
        bump = min(1.2, dist / 12) * math.sin(math.pi * p)
        ls = lerp(math.log(prev[2]), math.log(tgt[2]), p) - bump
        cam = (lerp(prev[0], tgt[0], p), lerp(prev[1], tgt[1], p), math.exp(ls), lerp(prev[3], tgt[3], p))
    # slow drift zoom
    return (cam[0], cam[1], cam[2] * (1 + 0.025 * max(0, lt - 0.85)), cam[3])

def proj(cam, lon, my):
    cx, cy, s, fy = cam
    return (lon - cx) * s + W / 2, -(my - cy) * s + fy

_OCEAN = None
def ocean():
    global _OCEAN
    if _OCEAN is None:
        a = np.linspace(0, 1, H)[:, None]
        r = (8 + 10 * a); g = (22 + 18 * a); b = (44 + 30 * a)
        img = np.repeat(np.stack([r, g, b], -1), W, 1).astype(np.uint8)
        _OCEAN = Image.fromarray(img, "RGB").convert("RGBA")
    return _OCEAN

def mix(c1, c2, k): return tuple(int(c1[i] * (1 - k) + c2[i] * k) for i in range(3))

def draw_map(cam, active=None, pulse=0.0, highlight_all=0.0):
    img = ocean().copy()
    d = aggdraw.Draw(img)
    cx, cy, s, fy = cam
    lon0 = cx - W / 2 / s; lon1 = cx + W / 2 / s
    my0 = cy - (H - fy) / s; my1 = cy + fy / s
    # graticule
    gp = aggdraw.Pen((120, 160, 230), 1.2, 40)
    step = 5 if s < 60 else 1
    for lo in range(int(lon0) // step * step, int(lon1) + step, step):
        x = (lo - cx) * s + W / 2; d.line((x, 0, x, H), gp)
    lat = -10
    while lat < 70:
        if lat % step == 0:
            y = -(merc_y(lat) - cy) * s + fy
            if -5 < y < H + 5: d.line((0, y, W, y), gp)
        lat += 1
    styles = {
        "other": ((38, 48, 72), None),
        "naichi": ((70, 86, 128), (150, 170, 220)),
        "hoppo": ((70, 86, 128), (150, 170, 220)),
    }
    order = ["other", "naichi", "hoppo", "chosen", "taiwan", "kanto", "karafuto", "nanyo"]
    for k in order:
        if k in LAYER_REG:
            base = REG[LAYER_REG[k]]
            on = (active == k)
            kk = 0.42 + 0.35 * highlight_all + (0.45 * (0.6 + 0.4 * pulse) if on else 0)
            fill = mix((38, 48, 72), base, min(1, kk))
            pen = aggdraw.Pen(mix(base, (255, 255, 255), 0.35 if on else 0), 3.0 if on else 1.5, 255)
        else:
            fill, pc = styles[k]
            if k == "hoppo" and active == "hoppo":
                fill = mix(fill, REG["北方領土"], 0.5 + 0.4 * pulse); pc = (255, 255, 255)
            pen = aggdraw.Pen(pc, 1.4, 200) if pc else None
        br = aggdraw.Brush(fill, 255)
        for poly, bb in zip(MAP[k], BB[k]):
            if bb[2] < lon0 or bb[0] > lon1 or bb[3] < my0 or bb[1] > my1: continue
            pts = np.empty((len(poly), 2), np.float32)
            pts[:, 0] = (poly[:, 0] - cx) * s + W / 2
            pts[:, 1] = -(poly[:, 1] - cy) * s + fy
            if (bb[2] - bb[0]) * s < 1.5 and (bb[3] - bb[1]) * s < 1.5:
                x, y = pts[0]; d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), None, br); continue
            if pen: d.polygon(pts.ravel().tolist(), pen, br)
            else: d.polygon(pts.ravel().tolist(), br)
    d.flush()
    return img

def glow_region(img, cam, layer, col, strength):
    if strength <= 0.01: return
    small = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
    d = aggdraw.Draw(small)
    cx, cy, s, fy = cam
    pen = aggdraw.Pen(col, 9, 255)
    for poly in MAP[layer]:
        pts = np.empty((len(poly), 2), np.float32)
        pts[:, 0] = ((poly[:, 0] - cx) * s + W / 2) / 2
        pts[:, 1] = (-(poly[:, 1] - cy) * s + fy) / 2
        if pts[:, 0].max() < -50 or pts[:, 0].min() > W or pts[:, 1].max() < -50 or pts[:, 1].min() > H: continue
        d.polygon(pts.ravel().tolist(), pen)
    d.flush()
    small = small.filter(ImageFilter.GaussianBlur(10))
    a = small.getchannel("A").point(lambda v: int(v * strength)); small.putalpha(a)
    img.alpha_composite(small.resize((W, H), Image.BILINEAR))

_OVL = None
def overlays():
    global _OVL
    if _OVL is None:
        o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        a = np.zeros((H, W), np.float32)
        y = np.arange(H)[:, None]
        a += np.clip((330 - y) / 330, 0, 1) * 200
        a += np.clip((y - 1020) / 160, 0, 1) * 215
        x = np.arange(W)[None, :]
        a += (np.clip((60 - x) / 60, 0, 1) + np.clip((x - (W - 60)) / 60, 0, 1)) * 80
        o = Image.fromarray(np.dstack([np.full((H, W), 5), np.full((H, W), 8), np.full((H, W), 18), np.clip(a, 0, 230)]).astype(np.uint8), "RGBA")
        _OVL = o
    return _OVL

def pin(c, x, y, col, lt=10, label=None, big=True, num=None, side="R"):
    d = ImageDraw.Draw(c)
    if big:
        drop = 1 - ease_back(lt / 0.35)
        yy = y - drop * 180
        for k in range(3):
            ph = ((lt * 0.9 + k / 3) % 1)
            r = 12 + ph * 70
            d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], outline=col + (int(200 * (1 - ph)),), width=4)
        d.ellipse([x - 9, y - 5, x + 9, y + 5], fill=(0, 0, 0, 120))
        # teardrop pin
        d.polygon([(x, yy), (x - 20, yy - 38), (x + 20, yy - 38)], fill=col + (255,))
        d.ellipse([x - 26, yy - 78, x + 26, yy - 26], fill=col + (255,), outline=(255, 255, 255, 255), width=4)
        d.ellipse([x - 10, yy - 62, x + 10, yy - 42], fill=(255, 255, 255, 255))
        if label and lt > 0.3:
            a = ease_out((lt - 0.3) / 0.3)
            im = text_img(label, F_DELA, 64, (255, 255, 255), 7, (10, 10, 25))
            lx = x + 40 if (side == "R" and x < W - 60 - im.width - 40) else x - 40 - im.width
            paste_l(c, im, lx, yy - 52, a)
    else:
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=col + (255,), outline=(255, 255, 255, 230), width=3)
        if num is not None:
            paste_c(c, text_img(str(num), F_DELA, 20, (15, 15, 25)), x, y)
        if label:
            paste_l(c, text_img(label, F_BLACK, 34, (255, 255, 255), 5, (10, 10, 25)), x + 20, y, 0.95)

def header(c, a=1):
    paste_c(c, text_img("戦前の外地", F_BLACK, 46, (255, 210, 90)), W / 2, 170, 1, a)
    paste_c(c, text_img("都市人口ランキング", F_DELA, 78, (255, 255, 255), 4, (20, 20, 40)), W / 2, 250, 1, a)

def legend(c, a=1):
    d = ImageDraw.Draw(c)
    x, y = 40, 1000
    for lb, col in (("内地", (70, 86, 128)), ("外地", (255, 120, 120))):
        if lb == "外地":
            for j, cc in enumerate((REG["朝鮮"], REG["台湾"], REG["関東州"])):
                d.rectangle([x + j * 10, y - 14, x + j * 10 + 10, y + 14], fill=mix((38, 48, 72), cc, 0.8) + (int(255 * a),))
        else:
            d.rectangle([x, y - 14, x + 30, y + 14], fill=col + (int(255 * a),), outline=(150, 170, 220, int(255 * a)))
        im = text_img(lb, F_BOLD, 30, (230, 230, 240), 3, (0, 0, 0))
        paste_l(c, im, x + 38, y, a); x += 38 + im.width + 30

def info_card(c, r, lt):
    city, ruby, reg, now, pop, shares, ll, extra = RANKS[r]
    acc = REG[reg] if r != 1 else (255, 200, 40)
    p = ease_out(lt / 0.35)
    d = ImageDraw.Draw(c)
    y0 = 1075 + (1 - p) * 120
    d.rounded_rectangle([40, y0, W - 40, y0 + 370], 34, fill=(12, 16, 36, int(225 * p)), outline=acc + (int(255 * p),), width=4)
    sc = 2.0 - 1.0 * ease_back(lt / 0.28)
    paste_c(c, text_img(str(r), F_DELA, 150, acc, 8, (10, 10, 25), glow=acc), 150, y0 + 125, sc, clamp(lt / 0.1))
    paste_c(c, text_img("位", F_DELA, 60, (255, 255, 255), 5, (10, 10, 25)), 150 + (45 if r < 10 else 95), y0 + 175, sc, clamp(lt / 0.1))
    if lt > 0.2:
        a = ease_out((lt - 0.2) / 0.3)
        tag = text_img(reg, F_BLACK, 34, (20, 20, 30))
        d.rounded_rectangle([300, y0 + 30, 300 + tag.width + 36, y0 + 82], 26, fill=acc + (int(255 * a),))
        paste_c(c, tag, 300 + (tag.width + 36) / 2, y0 + 56, 1, a)
        paste_l(c, text_img(ruby, F_BOLD, 36, (255, 230, 160), 3, (0, 0, 0)), 300 + tag.width + 56, y0 + 56, a)
        cim = text_img(city, F_DELA, 112, (255, 255, 255), 7, (10, 10, 25))
        paste_l(c, cim, 290 + (1 - a) * 80, y0 + 150, a)
        paste_l(c, text_img(now, F_BOLD, 34, (205, 215, 240), 3, (0, 0, 0)), 300, y0 + 232, a)
    if lt > 0.45:
        p4 = ease_out((lt - 0.45) / 0.6)
        val = int(round(pop * p4))
        im2 = text_img(f"{val}", F_DELA, 104, (255, 225, 110), 7, (10, 10, 25), glow=(255, 160, 0))
        im3 = text_img("万人", F_BLACK, 52, (255, 255, 255), 5, (10, 10, 25))
        im1 = text_img("約", F_BLACK, 52, (255, 255, 255), 5, (10, 10, 25))
        xr = W - 70
        pop_s = 1 + 0.15 * math.exp(-max(0, lt - 1.05) * 8) * (lt > 1.05)
        paste_c(c, im3, xr - im3.width / 2, y0 + 165)
        paste_c(c, im2, xr - im3.width - im2.width / 2 + 40, y0 + 145, pop_s)
        paste_c(c, im1, xr - im3.width - im2.width + 70 - im1.width / 2, y0 + 165)
    # bar
    pb = (lt - 0.9) / 0.7
    x0, bw, by, bh = 80, W - 160, y0 + 272, 30
    d.rounded_rectangle([x0 - 4, by - 4, x0 + bw + 4, by + bh + 4], 10, fill=(0, 0, 0, int(160 * p)))
    cols = [acc + (255,), (110, 125, 160, 255), (196, 150, 70, 255)]
    labels = ["内地人", ll, "外国人"]
    x = x0; tot = bw * ease_out(pb)
    for sh, col in zip(shares, cols):
        w = bw * sh / 100; w2 = max(0, min(w, x0 + tot - x))
        if w2 > 0: d.rectangle([x, by, x + w2, by + bh], fill=col)
        x += w
    a = clamp((pb - 0.5) / 0.5); lx = x0
    for sh, col, lb in zip(shares, cols, labels):
        if sh < 1 and lb != "外国人": continue
        d.rounded_rectangle([lx, by + 46, lx + 24, by + 70], 5, fill=col[:3] + (int(255 * a),))
        im = text_img(f"{lb} {sh}%" if sh >= 1 else f"{lb} 1%未満", F_BOLD, 30, (235, 235, 245), 3, (0, 0, 0))
        paste_l(c, im, lx + 32, by + 58, a); lx += im.width + 62

def callout(c, txt, x, y, lt):
    pe = ease_back((lt - 1.6) / 0.35)
    if lt < 1.6: return
    im = text_img(txt, F_BLACK, 44, (20, 20, 30))
    wpx = im.width + 56
    layer = Image.new("RGBA", (wpx + 20, 104), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([10, 10, wpx + 10, 94], 20, fill=(255, 225, 110, 255))
    layer.alpha_composite(im, (int((wpx + 20 - im.width) / 2), int((104 - im.height) / 2)))
    layer = layer.rotate(-4, expand=True, resample=Image.BICUBIC)
    x = min(max(x, layer.width / 2 + 30), W - layer.width / 2 - 30)
    paste_c(c, layer, x, y, pe)

REGION_LABELS = [("朝鮮", 127.6, 40.3), ("台湾", 125.6, 23.6), ("関東州", 117.0, 38.0), ("樺太", 147.8, 48.6), ("南洋群島", 147.0, 9.0)]

def frame(fi):
    t = fi / FPS
    sc = next((s for s in SCENES if s["start"] <= t < s["end"]), SCENES[-1])
    key = sc["key"]; lt = t - sc["start"]; dur = sc["end"] - sc["start"]
    cam = camera(t)
    is_rank = key.startswith("r") and key[1:].isdigit()
    r = int(key[1:]) if is_rank else None
    active = None; hl = 0.0
    if is_rank: active = REG_LAYER[RANKS[r][2]]
    elif key in EXTRAS: active = REG_LAYER[EXTRAS[key][0]]
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    if key == "title":
        order = ["chosen", "taiwan", "kanto", "karafuto", "nanyo"]
        k = int(lt / 0.55)
        active = order[k] if k < len(order) else None
        hl = clamp((lt - 2.75) / 0.3)
    if key in ("outro", "extra"): hl = 0.4
    c = draw_map(cam, active, pulse, hl)
    if active and active != "hoppo":
        glow_region(c, cam, active, REG[LAYER_REG[active]] if active in LAYER_REG else (255, 255, 255), 0.55 + 0.35 * pulse)
    elif active == "hoppo":
        glow_region(c, cam, "hoppo", REG["北方領土"], 0.6 + 0.4 * pulse)
    # tokyo reference
    tx, ty = proj(cam, 139.69, merc_y(35.68))
    if -50 < tx < W + 50 and -50 < ty < H and key not in EXTRAS:
        d = ImageDraw.Draw(c); d.rectangle([tx - 8, ty - 8, tx + 8, ty + 8], fill=(255, 255, 255, 230))
        paste_l(c, text_img("東京", F_BOLD, 28, (230, 230, 240), 3, (0, 0, 0)), tx + 14, ty)
    # previously revealed pins
    revealed = []
    if is_rank: revealed = [k for k in range(10, r, -1)]
    elif key in ("tease",): revealed = list(range(10, 1, -1))
    elif key in ("extra", "outro") or key in EXTRAS: revealed = list(range(10, 0, -1))
    for k in revealed:
        if key == "outro" and k <= 3: continue
        x, y = proj(cam, CITY[k][0], merc_y(CITY[k][1]))
        col = REG[RANKS[k][2]]
        lab = RANKS[k][0] if (cam[2] > 60 and key not in ("tease",)) else None
        pin(c, x, y, col, big=False, num=k, label=lab)
    # region labels on overview
    if key in ("title", "extra"):
        for i, (lb, lo, la) in enumerate(REGION_LABELS):
            show = (key == "title" and lt > i * 0.55) or key == "extra"
            if not show: continue
            if key == "extra" and lb not in ("樺太", "南洋群島"): continue
            x, y = proj(cam, lo, merc_y(la))
            a = ease_back((lt - (i * 0.55 if key == "title" else 0)) / 0.3)
            col = REG[lb if lb != "南洋群島" else "南洋"]
            paste_c(c, text_img(lb, F_DELA, 54, (255, 255, 255), 6, col), x, y, a)
        if key == "extra":
            x, y = proj(cam, 151.5, merc_y(44.0))
            paste_c(c, text_img("北方領土", F_DELA, 48, (255, 255, 255), 6, REG["北方領土"]), x, y, ease_back(lt / 0.3))
        x, y = proj(cam, 137.0, merc_y(37.6))
        paste_c(c, text_img("内地", F_DELA, 46, (255, 255, 255), 6, (70, 86, 128)), x, y, clamp(lt / 0.3))
    # current pin
    if is_rank and lt > 0.5:
        x, y = proj(cam, CITY[r][0], merc_y(CITY[r][1]))
        pin(c, x, y, REG[RANKS[r][2]] if r != 1 else (255, 200, 40), lt - 0.5, RANKS[r][0])
    if key in EXTRAS and lt > 0.6:
        for j, (nm, lo, la, *sd) in enumerate(EXTRA_PINS[key]):
            x, y = proj(cam, lo, merc_y(la))
            pin(c, x, y, REG[EXTRAS[key][0]], lt - 0.6 - j * 0.25, nm, side=(sd[0] if sd else "R")) if lt - 0.6 - j * 0.25 > 0 else None
    if key == "outro":
        for k in (3, 2, 1):
            x, y = proj(cam, CITY[k][0], merc_y(CITY[k][1]))
            pin(c, x, y, (255, 200, 40) if k == 1 else REG[RANKS[k][2]], big=False, num=k, label=RANKS[k][0])
    if key == "hook" and lt > 1.4:
        names = [("京城", 1), ("大連", 2), ("台北", 3), ("平壌", 4), ("釜山", 5), ("高雄", 10)]
        k = int((lt - 1.4) / 0.32) % len(names)
        nm, rk = names[k]
        x, y = proj(cam, CITY[rk][0], merc_y(CITY[rk][1]))
        d = ImageDraw.Draw(c)
        ph = ((lt - 1.4) / 0.32) % 1
        rr = 10 + 40 * ph
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 77, 109, int(255 * (1 - ph))), width=5)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(255, 77, 109, 255))
    if key == "tease":
        x, y = proj(cam, CITY[1][0], merc_y(CITY[1][1]))
        sh = (lt / dur) ** 2 * 10
        paste_c(c, text_img("?", F_DELA, 140, (255, 210, 90), 8, (10, 10, 25), glow=(255, 160, 0)),
                x + 120 + random.uniform(-sh, sh), y - 60 + random.uniform(-sh, sh), 0.8 + 0.5 * (lt / dur))
        c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (0.15 + 0.3 * lt / dur)))))
    c.alpha_composite(overlays())
    # UI layers
    if key == "hook":
        a = ease_out(lt / 0.4)
        paste_c(c, text_img("戦前の日本", F_BLACK, 66, (255, 210, 90), 6, (0, 0, 0)), W / 2, 190, 1, a)
        if lt > 0.4:
            paste_c(c, text_img("外地 最大の都市は？", F_DELA, 88, (255, 255, 255), 8, (10, 10, 25)), W / 2, 290, ease_back((lt - 0.4) / 0.4))
        if lt > 1.4:
            names = ["京城？", "大連？", "台北？", "平壌？", "釜山？", "高雄？"]
            k = int((lt - 1.4) / 0.32) % len(names); ph = ((lt - 1.4) / 0.32) % 1
            paste_c(c, text_img(names[k], F_DELA, 170, (255, 255, 255), 10, (10, 10, 25), glow=(255, 77, 109)), W / 2, 1230, 1.25 - 0.25 * ease_out(ph / 0.4))
    elif key == "title":
        header(c, ease_out(lt / 0.3))
        p = ease_back(lt / 0.35)
        paste_c(c, text_img("TOP10", F_DELA, 200, (255, 77, 109), 10, (255, 255, 255), glow=(255, 77, 109)), W / 2, 1210, (3 - 2 * ease_back(lt / 0.3)) * (1 + 0.04 * math.sin(lt * 10)))
        paste_c(c, text_img("朝鮮・台湾・関東州", F_BLACK, 52, (220, 230, 255), 5, (0, 0, 0)), W / 2, 1360, 1, ease_out((lt - 0.6) / 0.4))
        legend(c, ease_out((lt - 1) / 0.4))
    elif is_rank:
        header(c)
        info_card(c, r, lt)
        if RANKS[r][7]:
            x, y = proj(cam, CITY[r][0], merc_y(CITY[r][1]))
            callout(c, RANKS[r][7], x, max(420, y - 200), lt)
    elif key == "tease":
        header(c)
        paste_c(c, text_img("第1位は…", F_DELA, 140, (255, 255, 255), 8, (10, 10, 25)), W / 2, 1230, ease_back(lt / 0.3))
    elif key == "extra":
        paste_c(c, text_img("おまけ", F_DELA, 120, (255, 210, 90), 8, (10, 10, 25), glow=(255, 160, 0)), W / 2, 230, ease_back(lt / 0.35))
        paste_c(c, text_img("樺太・南洋・北方領土", F_BLACK, 60, (255, 255, 255), 6, (0, 0, 0)), W / 2, 1250, 1, ease_out((lt - 0.3) / 0.3))
    elif key in EXTRAS:
        extra_panel(c, key, lt)
    elif key == "outro":
        outro_panel(c, lt)
    if key == "r1": confetti(c, lt)
    vlt = t - sc["vstart"]
    if vlt > -0.1: subtitle(c, key, max(0, vlt))
    credit(c)
    flash = shake = 0
    if is_rank or key == "title":
        flash = max(0, 1 - lt / 0.25) * (0.8 if key in ("r1", "title") else 0.3)
        shake = max(0, 1 - lt / 0.3) * (30 if key in ("r1", "title") else 0)
    if key in ("extra", "outro"): flash = max(0, 1 - lt / 0.15) * 0.25
    if flash > 0: c.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * flash))))
    out = c.convert("RGB")
    if shake > 0:
        rr = random.Random(fi); dx, dy = int(rr.uniform(-shake, shake)), int(rr.uniform(-shake, shake))
        big = out.resize((int(W * 1.04), int(H * 1.04)), Image.BILINEAR)
        ox = (big.width - W) // 2 + dx; oy = (big.height - H) // 2 + dy
        out = big.crop((ox, oy, ox + W, oy + H))
    return out.tobytes()

def extra_panel(c, key, lt):
    reg, title, ruby, sub, stat, notes = EXTRAS[key]
    acc = REG[reg]
    paste_c(c, text_img("おまけ", F_DELA, 60, (255, 210, 90), 5, (10, 10, 25)), W / 2, 200)
    paste_c(c, text_img(title, F_DELA, 84 if len(title) <= 4 else 64, (255, 255, 255), 6, (10, 10, 25), glow=acc), W / 2, 285, ease_back(lt / 0.35))
    p = ease_out(lt / 0.35)
    d = ImageDraw.Draw(c)
    y0 = 1075 + (1 - p) * 120
    d.rounded_rectangle([40, y0, W - 40, y0 + 370], 34, fill=(12, 16, 36, int(225 * p)), outline=acc + (int(255 * p),), width=4)
    tag = text_img(reg, F_BLACK, 36, (20, 20, 30))
    d.rounded_rectangle([80, y0 + 30, 80 + tag.width + 36, y0 + 84], 27, fill=acc + (255,))
    paste_c(c, tag, 80 + (tag.width + 36) / 2, y0 + 57)
    paste_l(c, text_img(sub, F_BOLD, 34, (205, 215, 240), 3, (0, 0, 0)), 80 + tag.width + 60, y0 + 57)
    if lt > 0.4:
        paste_l(c, text_img(stat, F_DELA, 90, (255, 225, 110), 7, (10, 10, 25), glow=(255, 160, 0)), 70, y0 + 150, ease_out((lt - 0.4) / 0.3))
    for i, n in enumerate(notes):
        pn = ease_out((lt - 0.9 - i * 0.25) / 0.3)
        if pn > 0:
            paste_l(c, text_img("● " + n, F_BOLD, 38, (235, 235, 245), 3, (0, 0, 0)), 80 - (1 - pn) * 60, y0 + 238 + i * 50, pn)

def outro_panel(c, lt):
    paste_c(c, text_img("TOP3", F_DELA, 90, (255, 210, 90), 6, (10, 10, 25)), W / 2, 230, ease_back(lt / 0.3))
    rows = [("1", "京城", "約93万人", (255, 210, 90)), ("2", "大連", "約55万人", (220, 225, 235)), ("3", "台北", "約35万人", (230, 160, 100))]
    d = ImageDraw.Draw(c)
    for i, (r, n, p_, col) in enumerate(rows):
        pr = ease_back((lt - 0.2 - i * 0.15) / 0.35)
        if pr <= 0: continue
        y = 1060 + i * 100; x = 90 + (1 - pr) * -900
        d.rounded_rectangle([x, y, x + 900, y + 88], 24, fill=(12, 16, 36, 230), outline=col + (255,), width=4)
        paste_c(c, text_img(r, F_DELA, 60, col, 5, (10, 10, 25)), x + 60, y + 44)
        paste_l(c, text_img(n, F_DELA, 60, (255, 255, 255), 5, (10, 10, 25)), x + 120, y + 44)
        im = text_img(p_, F_BLACK, 48, (255, 225, 110), 4, (10, 10, 25))
        paste_c(c, im, x + 900 - 30 - im.width / 2, y + 44)
    if lt > 1.0:
        s = ease_back((lt - 1.0) / 0.35) * (1 + 0.04 * math.sin(lt * 7))
        paste_c(c, text_img("予想は当たった？", F_DELA, 76, (255, 255, 255), 7, (10, 10, 25), glow=(255, 77, 109)), W / 2, 345, s)
    if lt > 2.0:
        paste_c(c, text_img("ナレーション　VOICEVOX:青山龍星", F_BOLD, 34, (235, 235, 245), 4, (0, 0, 0)), W / 2, 1385, 1, ease_out((lt - 2) / 0.4))

def main():
    n = int(TOTAL * FPS)
    only = sys.argv[1:]
    if only:
        for s in only:
            Image.frombytes("RGB", (W, H), frame(int(float(s) * FPS))).save(os.path.join(HERE, f"map_{s}.png"))
        return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", os.path.join(HERE, "mix.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                           os.path.join(HERE, "out_map.mp4")], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(n), chunksize=8)):
            ff.stdin.write(b)
            if i % 300 == 0: print(i, "/", n, flush=True)
    ff.stdin.close(); ff.wait(); print("done")

if __name__ == "__main__":
    main()
