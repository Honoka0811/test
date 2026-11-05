import json, math, sys, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from common import *

Image.MAX_IMAGE_PIXELS = None
TL = json.load(open('timeline.json'))
SEGS = TL['segs']; TOTAL = TL['total']
SEG = {s['key']: s for s in SEGS}
RANKS = [s for s in SEGS if 'rank' in s]
BASE = Image.open('base.png').convert('RGB')

_fc = {}
def F(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_io(x): x = clamp(x); return 4*x*x*x if x < 0.5 else 1 - (-2*x + 2)**3 / 2
def ease_out(x): x = clamp(x); return 1 - (1 - x)**3
def ease_back(x, s=1.7):
    x = clamp(x); return 1 + (s + 1) * (x - 1)**3 + s * (x - 1)**2
def bounce(x):
    x = clamp(x); n1, d1 = 7.5625, 2.75
    if x < 1/d1: return n1*x*x
    if x < 2/d1: x -= 1.5/d1; return n1*x*x + .75
    if x < 2.5/d1: x -= 2.25/d1; return n1*x*x + .9375
    x -= 2.625/d1; return n1*x*x + .984375

def accent(rank):
    return {1: (245, 197, 66), 2: (205, 214, 226), 3: (214, 140, 72)}.get(rank, (64, 214, 200))
def hexa(c, a): return (c[0], c[1], c[2], int(a))

# ---------- camera ----------
def cam_for(key):
    s = SEG[key]
    if 'rank' in s and key != 'r1a':
        x, y = world(s['lon'], s['lat']); return (x, y, ZF, FOCUS_SY)
    return (FULL[0], FULL[1], FULL[2], FULL_SY)

def camera(t):
    prev = (FULL[0], FULL[1], FULL[2], FULL_SY)
    for s in SEGS:
        tgt = cam_for(s['key'])
        if t < s['start']:
            return prev
        if t < s['reveal'] and s['key'] != 'intro':
            e = ease_io((t - s['start']) / (s['reveal'] - s['start']))
            x = prev[0] + (tgt[0] - prev[0]) * e
            y = prev[1] + (tgt[1] - prev[1]) * e
            dist = math.hypot(tgt[0] - prev[0], tgt[1] - prev[1])
            lz = math.log(prev[2]) + (math.log(tgt[2]) - math.log(prev[2])) * e
            dip = min(0.45, dist * 0.18) * math.sin(math.pi * e)
            z = math.exp(lz) * (1 - dip)
            sy = prev[3] + (tgt[3] - prev[3]) * e
            return (x, y, z, sy)
        if t < s['end']:
            drift = 1 + 0.04 * (t - s['reveal']) / max(1e-6, s['end'] - s['reveal'])
            return (tgt[0], tgt[1], tgt[2] * drift, tgt[3])
        prev = tgt
    return prev

def to_screen(cam, wx, wy):
    cx, cy, z, sy = cam
    return (W/2 + (wx - cx) * z, sy + (wy - cy) * z)

def map_frame(cam):
    cx, cy, z, sy = cam
    l = (cx - (W/2) / z) * K; t = (cy - sy / z) * K
    r = l + W * K / z; b = t + H * K / z
    return BASE.transform((W, H), Image.EXTENT, (l, t, r, b), Image.BILINEAR)

# ---------- static assets ----------
def text_img(txt, font, fill, stroke=0, stroke_fill=(0, 0, 0), spacing=6, align='left'):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bb = d.multiline_textbbox((0, 0), txt, font=font, stroke_width=stroke, spacing=spacing, align=align)
    im = Image.new('RGBA', (int(math.ceil(bb[2] - bb[0])) + 4, int(math.ceil(bb[3] - bb[1])) + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).multiline_text((2 - bb[0], 2 - bb[1]), txt, font=font, fill=fill, stroke_width=stroke,
                                      stroke_fill=stroke_fill, spacing=spacing, align=align)
    return im

def rrect(size, radius, fill, outline=None, width=0, ss=2):
    w, h = size
    im = Image.new('RGBA', (w*ss, h*ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w*ss - 1, h*ss - 1), radius*ss, fill=fill, outline=outline, width=width*ss)
    return im.resize((w, h), Image.LANCZOS)

def fmt(n): return f'{n:,}'

PANEL_Y = 1150; PANEL_X = 50; PANEL_W = 980; PANEL_H = 300
def make_panel(s):
    c = accent(s['rank'])
    p = rrect((PANEL_W, PANEL_H), 36, (10, 20, 36, 225), outline=hexa(c, 255), width=4)
    # rank badge
    badge = rrect((300, 150), 30, hexa(c, 255))
    rt = text_img(f"第{s['rank']}位", F(DELA, 76), (18, 24, 34))
    badge.alpha_composite(rt, ((300 - rt.width)//2, (150 - rt.height)//2))
    name = text_img(s['name'], F(DELA, 104 if len(s['name']) <= 3 else 92), (255, 255, 255))
    note = text_img(s['note'], F(MPB, 34), (190, 205, 220)) if s.get('note') else None
    return dict(panel=p, badge=badge, name=name, note=note, c=c)

PANELS = {s['key']: make_panel(s) for s in RANKS if s['key'] != 'r1a'}
POP_FONT = F(DELA, 96); NIN_FONT = F(DELA, 54)

# header bar
def make_header():
    im = Image.new('RGBA', (W, 330), (0, 0, 0, 0))
    g = np.zeros((330, W, 4), np.uint8); g[:, :, :3] = (6, 14, 28)
    g[:, :, 3] = (np.clip(1.15 - np.linspace(0, 1, 330), 0, 1) * 230)[:, None].astype(np.uint8)
    im = Image.fromarray(g, 'RGBA')
    pill = rrect((470, 64), 32, (64, 214, 200, 255))
    pt = text_img('1940年（昭和15年）国勢調査', F(MPB, 32), (10, 24, 36))
    pill.alpha_composite(pt, ((470 - pt.width)//2, (64 - pt.height)//2 - 1))
    im.alpha_composite(pill, ((W - 470)//2, 92))
    tt = text_img('戦前の北海道 人口ランキング', F(DELA, 66), (255, 255, 255), stroke=4, stroke_fill=(6, 14, 28))
    im.alpha_composite(tt, ((W - tt.width)//2, 176))
    return im
HEADER = make_header()

CREDIT = text_img('VOICEVOX:四国めたん　／　音楽：魔王魂　／　効果音：効果音ラボ\n出典：昭和15年国勢調査報告（総務省統計局）', F(MPM, 26), (200, 212, 225, 230), stroke=2, stroke_fill=(6, 14, 28), spacing=8, align='center')

# intro title
T1 = text_img('戦前の北海道', F(DELA, 120), (255, 255, 255), stroke=8, stroke_fill=(6, 14, 28))
T2 = text_img('人口ランキング', F(DELA, 120), (255, 255, 255), stroke=8, stroke_fill=(6, 14, 28))
T3 = text_img('TOP 10', F(DELA, 150), (245, 197, 66), stroke=9, stroke_fill=(60, 30, 0))
T4 = text_img('1940年（昭和15年）国勢調査より', F(MPB, 46), (210, 235, 240), stroke=4, stroke_fill=(6, 14, 28))

Q1 = text_img('第1位は…？', F(DELA, 130), (245, 197, 66), stroke=9, stroke_fill=(40, 20, 0))

CAPS = {s['key']: text_img(s['sub'], F(MPB, 52), (255, 255, 255), stroke=6, stroke_fill=(8, 16, 30), spacing=14, align='center') for s in SEGS}

# outro ranking list
def make_list():
    w, h = 960, 1000
    im = rrect((w, h), 40, (8, 18, 34, 235), outline=(245, 197, 66, 255), width=4)
    hd = text_img('1940年 北海道の人口 TOP10', F(DELA, 54), (255, 255, 255))
    im.alpha_composite(hd, ((w - hd.width)//2, 36))
    rows = []
    for s in sorted([s for s in RANKS if s['key'] != 'r1a'], key=lambda s: s['rank']):
        r = Image.new('RGBA', (w - 60, 82), (0, 0, 0, 0)); d = ImageDraw.Draw(r)
        c = accent(s['rank'])
        bw = int(330 * s['pop'] / 206103)
        d.rounded_rectangle((300, 22, 300 + bw, 62), 10, fill=hexa(c, 170))
        rk = text_img(f"{s['rank']}", F(DELA, 52), c)
        r.alpha_composite(rk, (54 - rk.width//2, (82 - rk.height)//2))
        nm = text_img(s['name'], F(DELA, 46), (255, 255, 255))
        r.alpha_composite(nm, (100, (82 - nm.height)//2))
        pp = text_img(f"{fmt(s['pop'])}人", F(MPB, 42), (255, 255, 255), stroke=3, stroke_fill=(8, 18, 34))
        r.alpha_composite(pp, (w - 60 - pp.width - 6, (82 - pp.height)//2))
        rows.append(r)
    return im, rows
LIST_BG, LIST_ROWS = make_list()

# ---------- marker drawing (2x supersampled layer) ----------
SS = 2
def draw_markers(t, cam, layer):
    d = ImageDraw.Draw(layer)
    zf = cam[2] / Z0
    cur = None
    for s in RANKS:
        if s['key'] == 'r1a': continue
        if t >= s['start'] and t < s['end'] and t >= s['reveal'] - 0.0: cur = s
    # mystery markers in intro / before reveal
    intro = SEG['intro']
    for s in RANKS:
        if s['key'] == 'r1a': continue
        x, y = to_screen(cam, *world(s['lon'], s['lat']))
        if x < -100 or x > W + 100 or y < -100 or y > H + 100: continue
        X, Y = x*SS, y*SS
        revealed = t >= s['reveal']
        if not revealed:
            if t < intro['end'] + 0.0 or (s['key'] == 'r1' and t >= SEG['r1a']['start']):
                pulse = 0.5 + 0.5 * math.sin(t * 5 + s['rank'])
                a = clamp((t - 0.6 - (10 - s['rank']) * 0.12) / 0.3)
                if s['key'] == 'r1' and t >= SEG['r1a']['start']:
                    a = 1; r = (26 + 8 * pulse) * SS
                    d.ellipse((X - r, Y - r, X + r, Y + r), fill=(245, 197, 66, 220), outline=(255, 255, 255, 255), width=3*SS)
                    q = F(DELA, int(34 * SS)); d.text((X, Y), '?', font=q, fill=(40, 20, 0), anchor='mm')
                elif a > 0:
                    r = (14 + 3 * pulse) * SS
                    d.ellipse((X - r, Y - r, X + r, Y + r), fill=(120, 140, 160, int(200*a)), outline=(255, 255, 255, int(230*a)), width=2*SS)
                    q = F(DELA, int(20 * SS)); d.text((X, Y + 1), '?', font=q, fill=(255, 255, 255, int(255*a)), anchor='mm')
            continue
        c = accent(s['rank'])
        R = (9 + 40 * math.sqrt(s['pop'] / 206103)) * math.sqrt(zf) * SS
        is_cur = cur is s
        if is_cur:
            k = t - s['reveal']
            # pulse rings
            for j in range(2):
                ph = ((k + j * 0.5) % 1.0)
                rr = R + ph * 90 * SS
                d.ellipse((X - rr, Y - rr, X + rr, Y + rr), outline=hexa(c, 200 * (1 - ph)), width=4*SS)
            grow = ease_back(k / 0.4)
            Rg = R * grow
            d.ellipse((X - Rg, Y - Rg, X + Rg, Y + Rg), fill=hexa(c, 150), outline=(255, 255, 255, 255), width=3*SS)
            d.ellipse((X - 7*SS, Y - 7*SS, X + 7*SS, Y + 7*SS), fill=(255, 255, 255, 255))
            # pin drop
            drop = bounce(k / 0.55)
            py = Y - (1 - drop) * 400 * SS
            pr = 30 * SS; ph_ = py - 80 * SS
            d.polygon([(X, py), (X - pr * 0.82, ph_ + pr * 0.55), (X + pr * 0.82, ph_ + pr * 0.55)], fill=hexa(c, 255))
            d.ellipse((X - pr, ph_ - pr, X + pr, ph_ + pr), fill=hexa(c, 255), outline=(255, 255, 255, 255), width=3*SS)
            d.ellipse((X - pr*0.4, ph_ - pr*0.4, X + pr*0.4, ph_ + pr*0.4), fill=(255, 255, 255, 255))
        else:
            d.ellipse((X - R, Y - R, X + R, Y + R), fill=hexa(c, 120), outline=hexa((255, 255, 255), 220), width=2*SS)
            d.ellipse((X - 5*SS, Y - 5*SS, X + 5*SS, Y + 5*SS), fill=(255, 255, 255, 255))
    return cur

LABEL_OFF = {'r9': (1, 0.15), 'r8': (1, -0.85), 'r6': (1, 1.0), 'r3': (-1, -0.6), 'r1': (-1, 0.75), 'r2': (1, 0.2), 'r4': (1, 0.3)}
def draw_labels(t, cam, frame, cur):
    zf = cam[2] / Z0
    for s in RANKS:
        if s['key'] == 'r1a' or t < s['reveal']: continue
        x, y = to_screen(cam, *world(s['lon'], s['lat']))
        if s is cur:
            k = t - s['reveal']
            a = clamp((k - 0.35) / 0.25)
            if a <= 0: continue
            tag = text_img(s['name'], F(DELA, 50), (20, 24, 32))
            bg = rrect((tag.width + 40, tag.height + 26), 22, (255, 255, 255, 245))
            bg.alpha_composite(tag, (20, 13))
            if a < 1: bg.putalpha(bg.getchannel('A').point(lambda v: int(v * a)))
            frame.alpha_composite(bg, (int(x - bg.width / 2), int(y - 205 - bg.height)))
        else:
            sx, sy_ = LABEL_OFF.get(s['key'], (1, 0))
            R = (9 + 40 * math.sqrt(s['pop'] / 206103)) * math.sqrt(zf)
            lb = text_img(f"{s['rank']}位 {s['name']}", F(MPB, 30 if zf < 1.5 else 34), (255, 255, 255), stroke=4, stroke_fill=(8, 16, 30))
            lx = x + sx * (R + 10) + (0 if sx > 0 else -lb.width)
            ly = y + sy_ * lb.height * 1.6 - lb.height / 2
            frame.alpha_composite(lb, (int(lx), int(ly)))

def paste_alpha(frame, im, xy, a):
    if a <= 0: return
    if a < 1:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(xy[0]), int(xy[1])))

def scaled(im, s):
    if abs(s - 1) < 1e-3: return im
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)

# confetti
CONF_RNG = np.random.default_rng(3)
CONF = [dict(x=CONF_RNG.uniform(0, W), vy=CONF_RNG.uniform(260, 520), vx=CONF_RNG.uniform(-60, 60),
             y0=CONF_RNG.uniform(-900, -20), w=CONF_RNG.uniform(10, 20), h=CONF_RNG.uniform(16, 30),
             rot=CONF_RNG.uniform(0, 6.28), vr=CONF_RNG.uniform(-6, 6),
             c=[(245, 197, 66), (255, 255, 255), (64, 214, 200), (240, 90, 110), (120, 170, 255)][CONF_RNG.integers(0, 5)])
        for _ in range(170)]

def render(t):
    cam = camera(t)
    frame = map_frame(cam).convert('RGBA')
    # dim during r1a/outro
    dim = 0
    r1a, r1, out = SEG['r1a'], SEG['r1'], SEG['outro']
    if r1a['start'] <= t < r1['start']: dim = 0.45 * ease_out((t - r1a['start']) / 0.8)
    elif r1['start'] <= t < r1['reveal']: dim = 0.45 * (1 - ease_io((t - r1['start']) / 1.0))
    if t >= out['start']: dim = 0.55 * ease_out((t - out['start']) / 1.0)
    if t < 0.8: dim = max(dim, 1 - t / 0.8)
    if dim > 0: frame.alpha_composite(Image.new('RGBA', (W, H), (4, 10, 20, int(255 * dim))))
    # markers
    layer = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    cur = draw_markers(t, cam, layer)
    frame.alpha_composite(layer.resize((W, H), Image.BILINEAR))
    if t < out['start'] + 0.5:
        draw_labels(t, cam, frame, cur)
    intro = SEG['intro']
    # header (after intro)
    ha = clamp((t - intro['end'] + 0.6) / 0.6)
    paste_alpha(frame, HEADER, (0, 0), ha)
    # intro title
    if t < intro['end'] + 0.3:
        out_a = 1 - clamp((t - intro['end'] + 0.7) / 0.5)
        for i, (im, y) in enumerate([(T1, 470), (T2, 620), (T3, 780), (T4, 990)]):
            k = (t - 0.3 - i * 0.25) / 0.45
            if k <= 0: continue
            sc = 0.6 + 0.4 * ease_back(k) if i == 2 else 1
            im2 = scaled(im, sc)
            dy = (1 - ease_out(k)) * 60
            paste_alpha(frame, im2, ((W - im2.width) / 2, y + dy - (im2.height - im.height) / 2), clamp(k) * out_a)
    # rank panel
    for s in RANKS:
        if s['key'] in ('r1a',) or not (s['reveal'] <= t < s['end'] + 0.4): continue
        P = PANELS[s['key']]
        k = t - s['reveal']; ex = clamp((t - s['end']) / 0.35)
        a = clamp(k / 0.25) * (1 - ex)
        dy = (1 - ease_back(k / 0.45)) * 160 + ex * 120
        y0 = PANEL_Y + dy
        paste_alpha(frame, P['panel'], (PANEL_X, y0), a)
        bs = 0.4 + 0.6 * ease_back((k - 0.05) / 0.4, 2.5)
        b = scaled(P['badge'], bs)
        paste_alpha(frame, b, (PANEL_X + 30 + (300 - b.width) / 2, y0 + 30 + (150 - b.height) / 2), a)
        nk = clamp((k - 0.15) / 0.3)
        paste_alpha(frame, P['name'], (PANEL_X + 360 + (1 - ease_out(nk)) * 40, y0 + 30 + (150 - P['name'].height) / 2), a * nk)
        # population count-up
        ck = ease_out((k - 0.25) / 0.85)
        val = int(round(s['pop'] * ck))
        pt = text_img(fmt(val), POP_FONT, P['c'])
        nt = text_img('人', NIN_FONT, (255, 255, 255))
        px = PANEL_X + 40; py = y0 + 192
        paste_alpha(frame, pt, (px, py), a * clamp((k - 0.2) / 0.2))
        paste_alpha(frame, nt, (px + pt.width + 10, py + pt.height - nt.height - 4), a * clamp((k - 0.2) / 0.2))
        if P['note']:
            paste_alpha(frame, P['note'], (PANEL_X + PANEL_W - P['note'].width - 36, py + pt.height - P['note'].height - 6), a * clamp((k - 1.0) / 0.3))
    # #1 teaser
    if r1a['reveal'] - 0.2 <= t < r1['reveal']:
        k = t - r1a['reveal']
        sc = (0.5 + 0.5 * ease_back(k / 0.45)) * (1 + 0.04 * math.sin(t * 18))
        q = scaled(Q1, sc)
        fa = 1 - clamp((t - (r1['reveal'] - 0.25)) / 0.2)
        paste_alpha(frame, q, ((W - q.width) / 2, 1180 - q.height / 2), clamp(k / 0.2) * fa)
    # outro list
    if t >= out['start'] + 0.4:
        k = t - out['reveal'] + 0.4
        a = clamp(k / 0.4)
        y0 = 330 + (1 - ease_out(k / 0.5)) * 80
        paste_alpha(frame, LIST_BG, (60, y0), a)
        for i, row in enumerate(LIST_ROWS):
            rk = clamp((k - 0.3 - i * 0.09) / 0.3)
            paste_alpha(frame, row, (90 + (1 - ease_out(rk)) * 60, y0 + 120 + i * 86), rk)
    # caption
    for s in SEGS:
        st = s['voice'] - 0.05; en = s['voice'] + s['dur'] + 0.25
        if s['key'] == 'r1a': continue
        if st <= t < en:
            cap = CAPS[s['key']]
            a = clamp((t - st) / 0.2) * (1 - clamp((t - en + 0.2) / 0.2))
            y = 1478 if s['key'] not in ('intro', 'outro') else (1180 if s['key'] == 'intro' else 1360)
            paste_alpha(frame, cap, ((W - cap.width) / 2, y), a)
    # confetti for #1
    k = t - r1['reveal']
    if 0 <= k < 5.5:
        d = ImageDraw.Draw(frame)
        for c in CONF:
            y = c['y0'] + c['vy'] * k
            if y < -40 or y > H + 40: continue
            x = c['x'] + c['vx'] * k + 30 * math.sin(k * 3 + c['rot'])
            ang = c['rot'] + c['vr'] * k
            hw = c['w'] / 2 * abs(math.cos(ang * 0.7)) + 2; hh = c['h'] / 2
            ca, sa = math.cos(ang), math.sin(ang)
            pts = [(x + ca * dx - sa * dy, y + sa * dx + ca * dy) for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            d.polygon(pts, fill=c['c'] + (int(255 * (1 - clamp((k - 4.5) / 1.0))),))
    # flash at reveals
    for s in RANKS:
        if s['key'] == 'r1a': continue
        k = t - s['reveal']
        if 0 <= k < 0.3:
            fl = (1 - k / 0.3) * (0.55 if s['rank'] == 1 else 0.22)
            frame.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * fl))))
    # credit
    frame.alpha_composite(CREDIT, ((W - CREDIT.width) // 2, 1590))
    # fade out at end
    if t > TOTAL - 0.6:
        frame.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * clamp((t - TOTAL + 0.6) / 0.6)))))
    return frame.convert('RGB')

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[2:]:
            render(float(ts)).save(f'still_{ts}.png')
    else:
        i0, i1, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                              '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for i in range(i0, i1):
            p.stdin.write(render(i / FPS).tobytes())
        p.stdin.close(); p.wait()
