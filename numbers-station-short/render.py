"""映像レンダラ（1080x1920 / 30fps）。PIL で描画 → numpy でポストエフェクト → ffmpeg へパイプ。"""
import math
import re
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from scenes import HIDDEN, HIDDEN_FRAMES, FREQ_LOCK_SCENE

W, H, FPS = 1080, 1920, 30
JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
MONO_R = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

GREEN = (70, 255, 140)
RED = (255, 48, 60)
YELLOW = (255, 226, 70)
WHITE = (245, 245, 245)

# render 前に build.py が設定する
STATE = dict(scenes=None, total=0, audio=None, sr=48000)


@lru_cache(None)
def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(MONO_R, size)


# ---------- 事前計算 ----------
_rng = np.random.default_rng(4625)


def _make_static():
    yy = np.linspace(0, 1, H)[:, None]
    bg = np.zeros((H, W, 3), np.float32)
    bg[..., 0] = 6 + 8 * yy
    bg[..., 1] = 10 + 10 * yy
    bg[..., 2] = 16 + 14 * yy
    xx = np.linspace(-1, 1, W)[None, :]
    y2 = np.linspace(-1, 1, H)[:, None]
    vig = np.clip(1.15 - 0.55 * (xx ** 2 + (y2 * 0.8) ** 2), 0.25, 1.0).astype(np.float32)
    scan = np.ones((H, 1, 1), np.float32)
    scan[::3] = 0.82
    grain = [(_rng.standard_normal((H // 2, W // 2, 1)) * 6).astype(np.float32) for _ in range(6)]
    grain = [np.repeat(np.repeat(g, 2, 0), 2, 1) for g in grain]
    # 背景の数字レイン（縦長画像をスクロール）
    rain = Image.new("L", (W, H * 2), 0)
    d = ImageDraw.Draw(rain)
    f = font(MONO_R, 34)
    for x in range(20, W, 54):
        y = int(_rng.integers(0, 60))
        while y < H * 2:
            d.text((x, y), str(_rng.integers(0, 10)), font=f, fill=int(_rng.integers(25, 90)))
            y += 44
    rain = np.asarray(rain, np.float32)[..., None] / 255.0
    return bg, vig[..., None], scan, grain, rain


BG, VIG, SCAN, GRAIN, RAIN = _make_static()
RAIN_TINT = np.array([40, 140, 80], np.float32)


# ---------- 文字ユーティリティ ----------
def parse_caption(line):
    """'あ【い】う' -> [('あ',False),('い',True),('う',False)]"""
    out = []
    for part in re.split(r"(【[^】]*】)", line):
        if not part:
            continue
        if part.startswith("【"):
            out.append((part[1:-1], True))
        else:
            out.append((part, False))
    return out


@lru_cache(None)
def caption_image(text, hl_color=YELLOW):
    lines = [parse_caption(l) for l in text.split("\n")]
    size = 98
    while True:
        f = font(JP, size)
        widths = [sum(f.getlength(s) for s, _ in segs) for segs in lines]
        if max(widths) <= 940 or size <= 50:
            break
        size -= 4
    lh = int(size * 1.32)
    img = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for li, (segs, w) in enumerate(zip(lines, widths)):
        x = (W - w) / 2
        y = 20 + li * lh
        for s, hl in segs:
            col = hl_color if hl else WHITE
            # 影 → 太い縁取り → 本体
            d.text((x + 6, y + 8), s, font=f, fill=(0, 0, 0, 160), stroke_width=12, stroke_fill=(0, 0, 0, 160))
            d.text((x, y), s, font=f, fill=col, stroke_width=11, stroke_fill=(0, 0, 0, 255))
            d.text((x, y), s, font=f, fill=col, stroke_width=2, stroke_fill=col)  # 擬似ボールド
            x += f.getlength(s)
    return img


def text_c(d, xy, s, f, fill, stroke=0, sfill=(0, 0, 0)):
    d.text(xy, s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sfill)


def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


def stamp(img, label, cx, cy, angle, lt, appear, color=RED, size=110):
    if lt < appear:
        return
    k = ease_out((lt - appear) / 0.12)
    scale = 1.8 - 0.8 * k
    f = font(MONO, size)
    tw = int(f.getlength(label)) + 60
    th = size + 50
    s = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    a = int(230 * k)
    d.rectangle([4, 4, tw - 5, th - 5], outline=color + (a,), width=10)
    text_c(d, (tw / 2, th / 2), label, f, color + (a,))
    s = s.resize((int(tw * scale), int(th * scale)), Image.BILINEAR).rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


# ---------- 各シーンの演出 ----------
def v_radio(img, d, lt, dur, alert=False):
    x0, y0, x1, y1 = 80, 430, 1000, 760
    panel = (60, 34, 18) if not alert else (70, 14, 14)
    d.rounded_rectangle([x0, y0, x1, y1], 34, fill=panel, outline=(150, 100, 50), width=6)
    d.rounded_rectangle([x0 + 40, y0 + 50, x1 - 40, y0 + 210], 16, fill=(235, 190, 110) if not alert else (240, 120, 100))
    f = font(MONO, 34)
    for i in range(31):
        x = x0 + 70 + i * (x1 - x0 - 140) / 30
        L = 46 if i % 5 == 0 else 22
        d.line([x, y0 + 70, x, y0 + 70 + L], fill=(40, 25, 10), width=4)
        if i % 5 == 0:
            text_c(d, (x, y0 + 165), f"{3 + i // 5 * 2}", f, (40, 25, 10))
    nx = x0 + 300 + 260 * math.sin(lt * 0.9) + 14 * math.sin(lt * 13)
    d.line([nx, y0 + 55, nx, y0 + 205], fill=RED, width=8)
    text_c(d, ((x0 + x1) / 2, y0 + 270), "SHORTWAVE  RECEIVER", font(MONO, 40), (230, 200, 150))
    # 「聞こえてくる」5桁の数字
    rs = np.random.default_rng(int(lt * 2) + (99 if alert else 0))
    grp = "".join(str(v) for v in rs.integers(0, 10, 5))
    jit = rs.integers(-6, 7, 2)
    col = GREEN if not alert else RED
    text_c(d, (540 + jit[0], 920 + jit[1]), "  ".join(grp), font(MONO, 120), col, 6)
    if alert:
        if int(lt * 6) % 2 == 0:
            d.rectangle([12, 12, W - 13, H - 13], outline=RED, width=18)
        stamp(img, "CLASSIFIED", 540, 600, 12, lt, 0.3)


def v_title(img, d, lt, dur):
    cx, cy = 540, 700
    for k in range(6):
        r = ((lt * 220 + k * 120) % 720)
        a = int(max(0, 160 - r / 4.5))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 60, 60, a), width=5)
    f = font(JP, 200)
    g = 10 if lt < 0.25 or int(lt * 10) % 17 == 0 else 3
    for dx, col in [(-g, (255, 0, 60, 200)), (g, (0, 220, 255, 200))]:
        text_c(d, (cx + dx, cy), "乱数放送", f, col, 4, col)
    text_c(d, (cx, cy), "乱数放送", f, WHITE, 6, (0, 0, 0))
    text_c(d, (cx, cy + 170), "N U M B E R S   S T A T I O N", font(MONO, 44), RED)


TELEGRAM = ["指令  No.0476", "47193 08264 55107", "39820 61458 70315", "26941 83077 14582", "90613 52248 ■■■■■"]
TYPE_CPS = 22


def telegram_chars(dur):
    return sum(len(l) for l in TELEGRAM[1:])


def v_telegram(img, d, lt, dur):
    d.rectangle([90, 400, 990, 1060], fill=(214, 200, 168), outline=(120, 100, 70), width=6)
    d.line([130, 500, 950, 500], fill=(120, 100, 70), width=3)
    text_c(d, (540, 455), TELEGRAM[0], font(JP, 54), (60, 40, 30))
    n = int(lt * TYPE_CPS)
    f = font(MONO, 68)
    y = 580
    for line in TELEGRAM[1:]:
        shown = line[: max(0, n)]
        n -= len(line)
        d.text((150, y), shown, font=f, fill=(30, 30, 40))
        if 0 < len(shown) < len(line) and int(lt * 8) % 2 == 0:
            d.text((150 + f.getlength(shown), y), "▌", font=f, fill=(30, 30, 40))
        y += 115
    stamp(img, "TOP SECRET", 560, 760, -14, lt, 1.6)


OTP_P = [3, 8, 1, 0, 5]
OTP_K = [7, 2, 9, 4, 6]
OTP_C = [(a + b) % 10 for a, b in zip(OTP_P, OTP_K)]


def otp_tick_times():
    return [1.1 + i * 0.28 for i in range(5)]


def v_otp(img, d, lt, dur):
    fl = font(JP, 48)
    fd = font(MONO, 96)
    rows = [("平文", OTP_P, WHITE, 0.0), ("乱数表", OTP_K, YELLOW, 0.5), ("暗号", OTP_C, GREEN, 1.1)]
    for r, (label, digits, col, t0) in enumerate(rows):
        y = 470 + r * 190
        if r == 2:
            d.line([300, y - 95, 1000, y - 95], fill=WHITE, width=5)
            text_c(d, (250, y - 190), "+", font(MONO, 90), WHITE)
        slide = ease_out((lt - t0) / 0.3) if r == 1 else 1.0
        if lt < t0 and r == 1:
            continue
        off = (1 - slide) * 600
        d.text((40 + off, y - 28), label, font=fl, fill=col)
        for i, v in enumerate(digits):
            if r == 2 and lt < otp_tick_times()[i]:
                continue
            x = 360 + i * 130 + off
            d.rounded_rectangle([x - 55, y - 70, x + 55, y + 70], 14, outline=col, width=5)
            text_c(d, (x, y), str(v), fd, col)
    text_c(d, (540, 1050), "（各桁を足して 10 で割った余り）", font(JP, 40), (170, 170, 170))
    if lt > 3.0:
        stamp(img, "UNBREAKABLE", 560, 760, 9, lt, 3.0, size=96)


def buzz_gate(lt):
    return (lt % 1.5) < 1.0


def v_buzzer(img, d, lt, dur):
    on = buzz_gate(lt)
    r = 330 + (25 if on else 0)
    a = 150 if on else 50
    d.ellipse([540 - r, 720 - r, 540 + r, 720 + r], outline=(255, 40, 40, a), width=14)
    d.ellipse([540 - r + 40, 720 - r + 40, 540 + r - 40, 720 + r - 40], outline=(255, 40, 40, a // 2), width=6)
    text_c(d, (540, 560), "UVB-76", font(MONO, 96), RED if on else (150, 40, 40), 4)
    text_c(d, (540, 730), "4625", font(MONO, 230), GREEN, 6)
    text_c(d, (540, 870), "kHz", font(MONO, 70), GREEN)
    text_c(d, (540, 990), "BZZZZZ…" if on else "", font(MONO, 64), (255, 120, 120))


REDACT = ["受信ログ  04:17 UTC", "■■■■ ■■ 74 59", "■■ 18 52 ■■■■", "■■■■■ ■■■ ■■", "？？？？？"]


def v_redacted(img, d, lt, dur):
    d.rectangle([90, 420, 990, 1040], fill=(12, 16, 14), outline=(60, 120, 80), width=4)
    f = font(JP, 64)
    for i, line in enumerate(REDACT):
        if lt < i * 0.45:
            break
        col = GREEN if i == 0 else (200, 230, 210)
        if i == len(REDACT) - 1:
            col = RED if int(lt * 5) % 2 else (120, 20, 20)
        d.text((140, 470 + i * 110), line, font=f if i == 0 else font(JP, 72), fill=col)


def v_year(img, d, lt, dur):
    k = ease_out(lt / 1.3)
    year = int(2000 + 16 * k)
    flash = lt > 1.3 and lt < 1.45
    text_c(d, (540, 650), str(year), font(MONO, 260), YELLOW if not flash else WHITE, 8)
    # 2000 → 2016 の空白期間
    x0, x1 = 140, 940
    d.line([x0, 900, x1, 900], fill=(120, 120, 120), width=8)
    d.line([x0, 900, x0 + (x1 - x0) * k, 900], fill=RED, width=12)
    for x, s in [(x0, "2000 停止"), (x1, "2016 再開")]:
        d.ellipse([x - 16, 884, x + 16, 916], fill=RED)
        text_c(d, (x if x > 500 else x + 60, 970), s, font(JP, 44), WHITE)
    if lt > 1.3:
        text_c(d, (540, 470), "PYONGYANG", font(MONO, 64), (255, 140, 140))


RADAR_BLIPS = [(0.6, 220), (2.1, 300), (3.4, 150), (4.6, 330), (5.5, 250), (1.3, 120)]


def v_radar(img, d, lt, dur):
    cx, cy, R = 540, 720, 380
    for r in (R, R * 2 / 3, R / 3):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 160, 90), width=4)
    d.line([cx - R, cy, cx + R, cy], fill=(40, 120, 70), width=2)
    d.line([cx, cy - R, cx, cy + R], fill=(40, 120, 70), width=2)
    ang = (lt * 2.2) % (2 * math.pi)
    for k in range(18):
        a0 = math.degrees(ang) - k * 3
        d.pieslice([cx - R, cy - R, cx + R, cy + R], a0 - 3, a0, fill=(70, 255, 140, int(120 * (1 - k / 18))))
    for ba, br in RADAR_BLIPS:
        since = (ang - ba) % (2 * math.pi)
        a = int(255 * max(0, 1 - since / 3))
        if a > 0:
            x, y = cx + br * math.cos(ba), cy + br * math.sin(ba)
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(255, 80, 80, a))
            d.text((x + 24, y - 20), "??? kHz", font=font(MONO, 30), fill=(255, 160, 160, a))


def v_hidden(img, d, lt, dur):
    rs = np.random.default_rng(int(lt * 15))
    for i in range(4):
        x = 195 + i * 230
        y = 740
        d.rounded_rectangle([x - 90, y - 120, x + 90, y + 120], 18, outline=GREEN, width=7)
        ch = str(rs.integers(0, 10)) if (lt < 1.0 or int(lt * 3 + i) % 5 == 0) else "?"
        text_c(d, (x, y), ch, font(MONO, 160), GREEN if ch != "?" else WHITE)
    text_c(d, (540, 480), "見つけられる？", font(JP, 84), RED, 6)


VISUALS = dict(radio=v_radio, radio_alert=lambda *a: v_radio(*a, alert=True), title=v_title,
               telegram=v_telegram, otp=v_otp, buzzer=v_buzzer, redacted=v_redacted,
               year=v_year, radar=v_radar, hidden=v_hidden)


# ---------- 共通UI ----------
def header(d, t, scene):
    if int(t * 2) % 2 == 0:
        d.ellipse([70, 150, 104, 184], fill=RED)
    d.text((118, 142), "REC", font=font(MONO, 44), fill=RED)
    d.text((70, 200), "SW RECEIVER  CH-07", font=font(MONO, 30), fill=(120, 200, 150))
    locked = scene["lock"]
    if locked:
        fr = 4625.0
    else:
        fr = 3000 + (t * 1370) % 9000 + 30 * math.sin(t * 7)
    d.text((1010, 140), f"{fr:7.1f} kHz", font=font(MONO, 58), fill=GREEN if locked else (170, 255, 200), anchor="ra")
    for i in range(6):
        lvl = (math.sin(t * 9 + i) * 0.5 + 0.5) * (1 if locked else 0.6)
        col = GREEN if i / 6 < lvl else (40, 70, 50)
        d.rectangle([800 + i * 34, 252 - i * 6, 822 + i * 34, 262], fill=col)


def scope(d, t):
    a, sr = STATE["audio"], STATE["sr"]
    i0 = int(t * sr)
    n = int(0.04 * sr)
    seg = a[i0:i0 + n] if i0 < len(a) else np.zeros(n)
    if len(seg) < n:
        seg = np.pad(seg, (0, n - len(seg)))
    seg = seg[:: max(1, n // 220)]
    y0 = 1085
    pts = [(60 + i * 960 / (len(seg) - 1), y0 - float(v) * 90) for i, v in enumerate(seg)]
    d.line(pts, fill=(70, 255, 140, 220), width=4)
    d.line([60, y0, 1020, y0], fill=(40, 100, 60, 120), width=1)


def scene_at(t):
    sc = STATE["scenes"]
    for s in sc:
        if t < s["end"]:
            return s
    return sc[-1]


def glitch_amount(t):
    g = 0.0
    for s in STATE["scenes"][1:]:
        dt = t - s["start"]
        if 0 <= dt < 0.16:
            g = max(g, 1 - dt / 0.16)
    total = STATE["total"]
    if t < 0.35:
        g = max(g, 1.0)  # 冒頭は砂嵐から始まる
    if t > total - 0.9:
        g = max(g, (t - (total - 0.9)) / 0.9)  # 終わりは砂嵐へ（ループ）
    return g


def frame(i):
    t = i / FPS
    s = scene_at(t)
    lt = t - s["start"]
    dur = s["end"] - s["start"]

    off = int((t * 160) % H)
    base = BG + RAIN[off:off + H] * RAIN_TINT * 0.55
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    VISUALS[s["visual"]](ov, d, lt, dur)
    header(d, t, s)
    scope(d, t)
    img.alpha_composite(ov)

    # テロップ（ポップイン）
    cap = caption_image(s["caption"])
    k = ease_out(lt / 0.18)
    sc = 1.22 - 0.22 * k
    c = cap if sc == 1.0 else cap.resize((int(cap.width * sc), int(cap.height * sc)), Image.BILINEAR)
    img.alpha_composite(c, (int((W - c.width) / 2), int(1330 - c.height / 2)))

    # 隠し数字
    for si, at, digit, (hx, hy) in HIDDEN:
        st = STATE["scenes"][si]["start"] + at
        if st <= t < st + HIDDEN_FRAMES / FPS:
            hd = ImageDraw.Draw(img)
            text_c(hd, (hx, hy), digit, font(MONO, 180), (120, 255, 170), 4, (0, 60, 30))

    arr = np.asarray(img.convert("RGB"), np.float32)

    # ---- ポストエフェクト ----
    g = glitch_amount(t)
    rs = np.random.default_rng(i)
    if g > 0:
        for _ in range(int(3 + 10 * g)):
            y = int(rs.integers(0, H - 80))
            h = int(rs.integers(10, 120))
            arr[y:y + h] = np.roll(arr[y:y + h], int(rs.integers(-120, 120) * g), axis=1)
        sh = int(4 + 24 * g)
        arr[..., 0] = np.roll(arr[..., 0], sh, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -sh, axis=1)
        if g > 0.5:
            noise = rs.integers(0, 255, (H // 4, W // 4, 1)).astype(np.float32)
            noise = np.repeat(np.repeat(noise, 4, 0), 4, 1)
            arr = arr * (1 - (g - 0.5) * 1.6) + noise * (g - 0.5) * 1.6
    else:
        arr[..., 0] = np.roll(arr[..., 0], 2, axis=1)
    if s["visual"] == "buzzer" and buzz_gate(lt):
        arr = np.roll(arr, (int(rs.integers(-6, 7)), int(rs.integers(-6, 7))), axis=(0, 1))
    arr = arr * SCAN * VIG + GRAIN[i % len(GRAIN)]
    arr *= 1 + 0.03 * math.sin(t * 50)
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()
