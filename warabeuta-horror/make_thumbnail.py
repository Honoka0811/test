#!/usr/bin/env python3
"""サムネイル生成（make_video.py の絵をそのまま使う）.

  thumbnail.png          … 1280x720（YouTube 通常動画）
  thumbnail_vertical.png … 1080x1920（TikTok / Shorts のカバー）

赤丸は「わ・た・し・が」の4つだけ見せて、続きは隠す（ネタバレしない）。
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import make_video as mv

HERE = Path(__file__).resolve().parent
RED = (205, 28, 22)
SEPIA = np.array([1.08, 0.88, 0.64], np.float32)


def grade(img, sepia=0.85, vignette=1.25, seed=0):
    """セピア＋周辺減光＋粒子."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]
    keep = ((a[..., 0] > 110) & (a[..., 1] < 60) & (a[..., 2] < 60))[..., None]   # 赤丸はセピアにしない
    y = a @ np.array([0.3, 0.59, 0.11], np.float32)
    a = np.where(keep, a, a * (1 - sepia) + y[..., None] * SEPIA * sepia)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = np.clip(vignette - (((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h / 2) / (h * 0.6)) ** 2), 0, 1)[..., None]
    a = a * v + np.random.default_rng(seed).normal(0, 7, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def grandma_close():
    """こちらを向いて目が光る祖母（部屋の絵から切り出し）."""
    room = mv.room_frame(lamp=1.0, child_=True, eyes=1.0, turn=1.0)
    return room.crop((60, 560, 1020, 1520))       # 960x960


def paper_teaser():
    """赤丸の紙：最初の4列（わ・た・し・が）だけ."""
    img = mv.PAPER.copy()
    d = ImageDraw.Draw(img)
    for x, y, _ in mv.TARGETS[:4]:
        d.arc([x - 52, y - 50, x + 52, y + 52], 0, 360, fill=(200, 20, 16), width=8)
    x0 = mv.PAPER_COLS[3] - 75
    x1 = mv.PAPER_COLS[0] + 75
    return img.crop((x0, 330, x1, 1400))


def stroke_text(d, xy, text, fnt, fill, sw=8, anchor="la"):
    d.text(xy, text, font=fnt, fill=fill, stroke_width=sw, stroke_fill=(0, 0, 0), anchor=anchor)


def landscape():
    W, H = 1280, 720
    base = Image.new("RGB", (W, H), (10, 7, 5))
    g = grandma_close().resize((720, 720))
    base.paste(g, (-40, 0))
    p = paper_teaser()
    ph = 760
    p = p.resize((int(p.width * ph / p.height), ph)).rotate(-4, expand=True, fillcolor=(10, 7, 5))
    base.paste(p, (W - p.width + 40, -30))
    base = grade(base, seed=1)
    # 紙と部屋の境目をなじませる
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(160):
        sd.line([(600 + i, 0), (600 + i, H)], fill=int(150 * (1 - abs(i - 80) / 80)))
    base = Image.composite(Image.new("RGB", (W, H), (8, 5, 4)), base, shade.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(base)
    stroke_text(d, (40, 470), "赤丸の文字を", mv.font(mv.MINCHO, 92), (245, 238, 225))
    stroke_text(d, (40, 575), "読んではいけない", mv.font(mv.MINCHO, 104), RED)
    stroke_text(d, (44, 40), "祖母の数え歌", mv.font(mv.MINCHO, 60), (235, 225, 205), sw=6)
    base.save(HERE / "thumbnail.png")


def vertical():
    W, H = 1080, 1920
    base = Image.new("RGB", (W, H), (10, 7, 5))
    p = paper_teaser()
    p = p.resize((int(p.width * 1000 / p.height), 1000)).rotate(-3, expand=True, fillcolor=(10, 7, 5))
    base.paste(p, ((W - p.width) // 2, 60))
    g = grandma_close().resize((1080, 1080))
    fade = Image.linear_gradient("L").resize((1080, 260))        # 上端をぼかして紙となじませる
    mask = Image.new("L", (1080, 1080), 255)
    mask.paste(fade, (0, 0))
    base.paste(g, (0, 840), mask)
    base = grade(base, seed=2, vignette=1.3)
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(300):
        sd.line([(0, 720 + i), (W, 720 + i)], fill=int(235 * (1 - abs(i - 150) / 150)))
    base = Image.composite(Image.new("RGB", (W, H), (8, 5, 4)), base, shade.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(base)
    stroke_text(d, (W / 2, 960), "赤丸の文字を", mv.font(mv.MINCHO, 104), (245, 238, 225), anchor="mm")
    stroke_text(d, (W / 2, 1090), "読んではいけない", mv.font(mv.MINCHO, 118), RED, anchor="mm")
    stroke_text(d, (W / 2, 1790), "祖母の数え歌", mv.font(mv.MINCHO, 76), (235, 225, 205), sw=6, anchor="mm")
    base.save(HERE / "thumbnail_vertical.png")


if __name__ == "__main__":
    landscape()
    vertical()
    print("saved thumbnail.png, thumbnail_vertical.png")
