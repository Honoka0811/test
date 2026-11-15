"""京都大学のここがすごい！10選 ショート動画レンダラー (1080x1920, 30fps)
- ナレーション: build/voice.json (tts.py で生成)
- BGM: numpy で自作合成(著作権フリー)
- 映像: PIL でフレーム描画 → ffmpeg
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from script import ITEMS

BUILD = os.path.join(HERE, "build")
W, H, FPS, SR = 1080, 1920, 30, 48000
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
ITEM = {it[0]: it for it in ITEMS}

# ---------------------------------------------------------------- timeline
segs = json.load(open(os.path.join(BUILD, "voice.json")))
LINE_GAP, LEAD, TAIL = 0.12, 0.25, 0.45
t = 0.0
for s in segs:
    s["start"] = t
    t += LEAD
    for ln in s["lines"]:
        ln["start"] = t
        t += ln["dur"] + LINE_GAP
    t += TAIL if s["kind"] != "outro" else 1.6
    s["end"] = t
TOTAL = t
NFR = int(math.ceil(TOTAL * FPS))
print(f"total {TOTAL:.2f}s, {NFR} frames")


# ---------------------------------------------------------------- audio
def read_wav(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return a.reshape(-1, w.getnchannels()).mean(axis=1)


N = int(TOTAL * SR) + SR
voice = np.zeros(N, np.float32)
for s in segs:
    for ln in s["lines"]:
        a = read_wav(ln["wav"])
        i = int(ln["start"] * SR)
        voice[i:i + len(a)] += a


def env(n, a=0.002, d=0.2):
    tt = np.arange(n) / SR
    return np.minimum(tt / a, 1) * np.exp(-tt / d)


def note_hz(m):
    return 440 * 2 ** ((m - 69) / 12)


BPM = 124
beat = 60 / BPM
bgm = np.zeros(N, np.float32)
rng = np.random.default_rng(7)
# I-V-vi-IV in F major
CHORDS = [[53, 57, 60], [48, 52, 55], [50, 53, 57], [46, 50, 53]]


def add(buf, i, sig):
    if i >= len(buf):
        return
    sig = sig[:len(buf) - i]
    buf[i:i + len(sig)] += sig


nbeats = int(TOTAL / beat) + 4
for b in range(nbeats):
    t0 = b * beat
    i0 = int(t0 * SR)
    bar = b // 4
    ch = CHORDS[bar % 4]
    # kick
    n = int(0.3 * SR); tt = np.arange(n) / SR
    f = 50 + 110 * np.exp(-tt * 30)
    add(bgm, i0, 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9))
    # clap on 2 & 4
    if b % 2 == 1:
        n = int(0.18 * SR)
        add(bgm, i0, 0.16 * rng.standard_normal(n) * env(n, 0.001, 0.05))
    # hats on offbeats
    for k in (0.5,):
        n = int(0.05 * SR)
        hat = rng.standard_normal(n); hat = np.diff(hat, prepend=0)
        add(bgm, int((t0 + k * beat) * SR), 0.05 * hat * env(n, 0.0005, 0.015))
    # bass: root, eighth notes
    for k in (0, 0.5):
        n = int(beat * 0.45 * SR); tt = np.arange(n) / SR
        fz = note_hz(ch[0] - 12)
        sig = np.sin(2 * np.pi * fz * tt) + 0.35 * np.sin(4 * np.pi * fz * tt)
        add(bgm, int((t0 + k * beat) * SR), 0.22 * sig * env(n, 0.004, 0.12) * (1 if k == 0 else 0.7))
    # pluck arpeggio, 16ths
    pat = [0, 1, 2, 1]
    for k in range(4):
        m = ch[pat[k]] + 12 + (12 if (b % 2 and k == 2) else 0)
        n = int(0.25 * SR); tt = np.arange(n) / SR
        fz = note_hz(m)
        sig = np.sin(2 * np.pi * fz * tt) + 0.3 * np.sin(4 * np.pi * fz * tt) + 0.1 * np.sin(6 * np.pi * fz * tt)
        add(bgm, int((t0 + k * beat / 4) * SR), 0.06 * sig * env(n, 0.002, 0.09))
    # pad: chord on bar start
    if b % 4 == 0:
        n = int(4 * beat * SR); tt = np.arange(n) / SR
        pad = sum(np.sin(2 * np.pi * note_hz(m) * tt) + 0.5 * np.sin(2 * np.pi * note_hz(m) * 1.003 * tt) for m in ch)
        e = np.minimum(tt / 0.3, 1) * np.minimum((n / SR - tt) / 0.3, 1)
        add(bgm, i0, 0.035 * pad * e)
    # simple melody every other bar
    if bar % 2 == 1 and b % 4 in (0, 2):
        m = ch[2] + 24 if b % 4 == 0 else ch[1] + 24
        n = int(beat * 1.6 * SR); tt = np.arange(n) / SR
        sig = np.sin(2 * np.pi * note_hz(m) * tt + 0.4 * np.sin(2 * np.pi * 5 * tt))
        add(bgm, i0, 0.045 * sig * env(n, 0.01, 0.35))

# fade in/out
fi = int(0.5 * SR); bgm[:fi] *= np.linspace(0, 1, fi)
fo = int(2.0 * SR); end = int(TOTAL * SR); bgm[end - fo:end] *= np.linspace(1, 0, fo); bgm[end:] = 0

# ducking: 声があるときBGMを下げる
ve = np.abs(voice)
k = int(0.08 * SR)
ve = np.convolve(ve, np.ones(k) / k, mode="same")
duck = 1 - 0.55 * np.clip(ve / 0.03, 0, 1)
duck = np.convolve(duck, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
bgm *= duck * 0.55

# SE: シーン切り替えの「ポン」
se = np.zeros(N, np.float32)
for s in segs:
    n = int(0.25 * SR); tt = np.arange(n) / SR
    f = 600 + 900 * np.exp(-tt * 25)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.07)
    add(se, int(s["start"] * SR), 0.28 * sig)

mix = voice * 1.0 + bgm + se
mix = np.tanh(mix * 1.1) * 0.92
pcm = (np.clip(mix[:int(TOTAL * SR)], -1, 1) * 32767).astype(np.int16)
apath = os.path.join(BUILD, "mix.wav")
with wave.open(apath, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("audio ok")

# ---------------------------------------------------------------- graphics
_fc = {}


def font(sz):
    if sz not in _fc:
        _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]


def text_bold(d, xy, txt, sz, fill, stroke=None, sw=0, anchor="mm", bold=2):
    f = font(sz)
    if stroke and sw:
        d.text(xy, txt, font=f, fill=stroke, stroke_width=sw + bold, stroke_fill=stroke, anchor=anchor)
    d.text(xy, txt, font=f, fill=fill, stroke_width=bold, stroke_fill=fill, anchor=anchor)


def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox())
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def wrap(txt, sz, maxw):
    """数字の連続や句読点で切らないよう、トークン単位でバランスよく折り返す"""
    import re
    f = font(sz)
    toks = re.findall(r"[0-9,]+[年人位選]?[、。！？]*|[ァ-ヶー]+[、。！？]*|.[、。！？」）]*", txt)
    n = math.ceil(f.getlength(txt) / maxw)
    target = min(maxw, f.getlength(txt) / n + sz * 1.5)
    lines, cur = [], ""
    for tk in toks:
        if cur and f.getlength(cur + tk) > target:
            lines.append(cur); cur = tk
        else:
            cur += tk
    if cur:
        lines.append(cur)
    return lines


def ease_out_back(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


# 背景 (濃紺グラデーション + 斜めストライプ)
yy = np.linspace(0, 1, H)[:, None, None]
top, bot = np.array([10, 24, 66]), np.array([28, 64, 140])
bg = (top * (1 - yy) + bot * yy).repeat(W, axis=1)
xx = np.arange(W)[None, :]
stripe = (((xx + np.arange(H)[:, None]) // 60) % 2 == 0)[:, :, None]
bg = np.where(stripe, bg * 1.06, bg).clip(0, 255).astype(np.uint8)
BG = Image.fromarray(bg, "RGB").convert("RGBA")

bokeh = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(30, 120), rng.uniform(0.2, 0.6), rng.uniform(0, 6.28))
         for _ in range(14)]

# ヘッダー
HEADER = Image.new("RGBA", (W, 330), (0, 0, 0, 0))
d = ImageDraw.Draw(HEADER)
d.rounded_rectangle((40, 50, W - 40, 300), 36, fill=(200, 30, 50, 255))
d.rounded_rectangle((40, 50, W - 40, 300), 36, outline=(255, 255, 255, 255), width=6)
text_bold(d, (W // 2, 120), "京都大学の", 72, (255, 255, 255), (120, 0, 20), 6)
text_bold(d, (W // 2, 225), "ここがすごい！10選", 108, (255, 230, 60), (90, 0, 10), 10, bold=3)

RANK_COL = {1: (255, 196, 30), 2: (200, 210, 225), 3: (215, 130, 60)}


def make_card(rank):
    _, title, sub, emo, _ = ITEM[rank]
    cw, ch = 940, 900
    im = Image.new("RGBA", (cw + 40, ch + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 34, cw + 20, ch + 34), 50, fill=(0, 0, 20, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, cw + 20, ch + 20), 50, fill=(255, 252, 245, 255))
    col = RANK_COL.get(rank, (40, 90, 200))
    d.rounded_rectangle((20, 20, cw + 20, ch + 20), 50, outline=col + (255,), width=14)
    # 絵文字の背後に円
    cx = (cw + 40) // 2
    d.ellipse((cx - 190, 150, cx + 190, 530), fill=tuple(int(c * 0.25 + 255 * 0.75) for c in col) + (255,))
    tsz = 150 if len(title) <= 5 else (120 if len(title) <= 7 else 100)
    text_bold(d, (cx, 650), title, tsz, (20, 30, 70), (255, 255, 255), 0, bold=3)
    d.rounded_rectangle((cx - 400, 760, cx + 400, 850), 45, fill=(20, 40, 100, 255))
    text_bold(d, (cx, 806), sub, 52, (255, 255, 255), bold=1)
    return im, emoji_img(emo, 300)


def make_badge(rank):
    col = RANK_COL.get(rank, (230, 40, 60))
    im = Image.new("RGBA", (420, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 410, 180), 40, fill=col + (255,), outline=(255, 255, 255, 255), width=8)
    txt_col = (60, 30, 0) if rank <= 3 else (255, 255, 255)
    text_bold(d, (210, 100), f"第{rank}位", 110, txt_col, bold=3)
    return im.rotate(6, resample=Image.BICUBIC, expand=True)


CARDS = {r: make_card(r) for r in ITEM}
BADGES = {r: make_badge(r) for r in ITEM}
CREDIT = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
text_bold(ImageDraw.Draw(CREDIT), (W - 30, 30), "VOICEVOX:四国めたん", 30, (255, 255, 255), (0, 0, 0), 3,
          anchor="rm", bold=0)

INTRO_EMO = emoji_img("🎓", 380)
OUTRO_EMO = emoji_img("💬", 300)
_cap = {}


def caption(txt):
    if txt not in _cap:
        lines = wrap(txt, 64, 960)
        im = Image.new("RGBA", (W, 98 * len(lines) + 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i, l in enumerate(lines):
            text_bold(d, (W // 2, 70 + i * 98), l, 64, (255, 255, 255), (10, 10, 30), 10, bold=2)
        _cap[txt] = im
    return _cap[txt]


def paste_scaled(dst, im, cx, cy, s, alpha=1.0):
    if s <= 0.01:
        return
    if abs(s - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    dst.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def progress(d, rank_now):
    # 10..1 の進捗ドット
    for i, r in enumerate(range(10, 0, -1)):
        x = W // 2 - 9 * 45 + i * 90
        y = 1440
        done = rank_now is not None and r >= rank_now
        cur = r == rank_now
        rad = 26 if cur else 18
        col = RANK_COL.get(r, (255, 90, 110)) if done else (255, 255, 255, 70)
        d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=col)
        if cur:
            d.ellipse((x - rad - 6, y - rad - 6, x + rad + 6, y + rad + 6), outline=(255, 255, 255), width=4)


def frame(fi):
    t = fi / FPS
    im = BG.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for (bx, by, br, sp, ph) in bokeh:
        y = (by - t * 40 * sp) % (H + 300) - 150
        x = bx + 30 * math.sin(t * sp + ph)
        od.ellipse((x - br, y - br, x + br, y + br), fill=(255, 255, 255, 22))
    im.alpha_composite(ov)

    s = next(s for s in segs if s["start"] <= t < s["end"] + 1e-6) if t < segs[-1]["end"] else segs[-1]
    lt = t - s["start"]
    kind = s["kind"]
    d = ImageDraw.Draw(im)

    if kind == "intro":
        sc = ease_out_back(lt / 0.5)
        paste_scaled(im, INTRO_EMO, W // 2, 600 + 15 * math.sin(t * 3), sc)
        title = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
        td = ImageDraw.Draw(title)
        text_bold(td, (W // 2, 110), "京都大学の", 120, (255, 255, 255), (150, 0, 30), 10, bold=3)
        text_bold(td, (W // 2, 270), "ここがすごい！", 140, (255, 230, 60), (150, 0, 30), 12, bold=4)
        text_bold(td, (W // 2, 430), "10選", 170, (255, 80, 100), (255, 255, 255), 10, bold=4)
        paste_scaled(im, title, W // 2, 1110, ease_out_back((lt - 0.2) / 0.5) * (1 + 0.02 * math.sin(t * 6)))
    else:
        im.alpha_composite(HEADER, (0, int(-330 * (1 - ease_out((t - segs[1]["start"]) / 0.4)))))
        if kind == "item":
            r = s["rank"]
            card, emo = CARDS[r]
            sc = ease_out_back(lt / 0.45)
            paste_scaled(im, card, W // 2, 860, sc)
            if sc > 0.5:
                paste_scaled(im, emo, W // 2, 860 - 470 + 340 + 14 * math.sin(t * 4), sc * (1 + 0.04 * math.sin(t * 8)))
            bx = -300 + (250 + 300) * ease_out((lt - 0.15) / 0.35)
            paste_scaled(im, BADGES[r], bx, 420, 1)
            progress(d, r)
        else:  # outro
            sc = ease_out_back(lt / 0.5)
            paste_scaled(im, OUTRO_EMO, W // 2, 700 + 12 * math.sin(t * 4), sc)
            box = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
            bd = ImageDraw.Draw(box)
            text_bold(bd, (W // 2, 110), "どれが一番", 120, (255, 255, 255), (20, 20, 60), 10, bold=3)
            text_bold(bd, (W // 2, 260), "すごかった？", 130, (255, 230, 60), (150, 0, 30), 12, bold=4)
            paste_scaled(im, box, W // 2, 1100, ease_out_back((lt - 0.2) / 0.5))
            progress(d, 1)

    # 字幕
    for ln in s["lines"]:
        if ln["start"] - 0.05 <= t < ln["start"] + ln["dur"] + LINE_GAP + (TAIL if ln is s["lines"][-1] else 0):
            c = caption(ln["text"])
            a = ease_out((t - ln["start"] + 0.05) / 0.12)
            paste_scaled(im, c, W // 2, 1540 + c.height / 2 + 20 * (1 - a), 1, a)
            break
    im.alpha_composite(CREDIT, (0, H - 70))
    return im.convert("RGB")


if __name__ == "__main__":
    if len(sys.argv) > 1:  # プレビュー: python render.py 秒...
        for sec in sys.argv[1:]:
            frame(int(float(sec) * FPS)).save(os.path.join(BUILD, f"preview_{sec}.png"))
        sys.exit()
    out = os.path.join(HERE, "kyoto_univ_sugoi10.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", apath,
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for fi in range(NFR):
        p.stdin.write(frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{NFR}", flush=True)
    p.stdin.close(); p.wait()
    print("done", out)
