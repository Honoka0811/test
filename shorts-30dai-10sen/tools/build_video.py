"""Compose the short video frames (1080x1920 @30fps) and pipe into ffmpeg."""
import json, math, os, sys, subprocess
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.environ.get('SCRATCH')
W, H, FPS = 1080, 1920, 30
A = f'{S}/assets'; F = f'{S}/dl/fonts'
FONT_TITLE = f'{F}/ZenMaruGothic-Black.ttf'
FONT_SUB = f'{F}/MPLUSRounded1c-Black.ttf'
FONT_KICK = f'{F}/MPLUSRounded1c-ExtraBold.ttf'
FONT_NUM = f'{F}/DelaGothicOne-Regular.ttf'
CREAM = (255, 250, 243)
INK = (38, 38, 52)

lines = {l['key']: l for l in json.load(open(f'{S}/voice/lines.json'))}

ITEMS = [
 dict(key='intro', kind='intro', accent='#FF6B6B', title=['30代のうちに', 'やっておくべきこと'],
      heroes=['UndrawCelebration', 'UndrawYoungAndHappy'], emojis=['party_popper', 'sparkles', 'confetti_ball', 'glowing_star']),
 dict(key='01', num=1, accent='#2EC4B6', title=['健康に投資する'], heroes=['UndrawHealthyHabit', 'UndrawJogging'],
      emojis=['flexed_biceps', 'running_shoe', 'stethoscope', 'green_salad']),
 dict(key='02', num=2, accent='#FFB703', title=['お金を仕組み化する'], heroes=['UndrawFinance', 'UndrawGrowing'],
      emojis=['money_bag', 'chart_increasing', 'coin', 'yen_banknote']),
 dict(key='03', num=3, accent='#7B61FF', title=['自分の武器を磨く'], heroes=['UndrawPowerful', 'UndrawFocus'],
      emojis=['trophy', 'light_bulb', 'brain', 'hundred_points']),
 dict(key='04', num=4, accent='#FF6B9A', title=['人間関係を整える'], heroes=['UndrawFriendship', 'UndrawHighFive'],
      emojis=['people_hugging', 'red_heart', 'two_hearts', 'clinking_glasses']),
 dict(key='05', num=5, accent='#3A86FF', title=['親と旅行に行く'], heroes=['UndrawTrip', 'UndrawDeparting'],
      emojis=['airplane', 'luggage', 'hot_springs', 'mount_fuji']),
 dict(key='06', num=6, accent='#FF5E5B', title=['大きく挑戦する'], heroes=['UndrawToTheStars', 'UndrawBeTheHero'],
      emojis=['rocket', 'fire', 'collision', 'briefcase']),
 dict(key='07', num=7, accent='#06D6A0', title=['住環境を整える'], heroes=['UndrawRelaxingAtHome', 'UndrawHouses'],
      emojis=['house_with_garden', 'couch_and_lamp', 'potted_plant', 'bed']),
 dict(key='08', num=8, accent='#F77F00', title=['学び直しをする'], heroes=['UndrawStudying', 'UndrawBibliophile'],
      emojis=['books', 'graduation_cap', 'pencil', 'open_book']),
 dict(key='09', num=9, accent='#C77DFF', title=['一生モノの趣味'], heroes=['UndrawMoreMusic', 'UndrawCamping'],
      emojis=['guitar', 'artist_palette', 'camping', 'fishing_pole']),
 dict(key='10', num=10, accent='#00B4D8', title=['今を記録に残す'], heroes=['UndrawPhotos', 'UndrawMomentToRemember'],
      emojis=['camera_with_flash', 'notebook', 'framed_picture', 'memo']),
 dict(key='outro', kind='outro', accent='#FF6B6B', title=['全部やらなくてOK', 'ひとつ選んで今日から'],
      heroes=['UndrawSuperhero', 'UndrawWelcome'], emojis=['thumbs_up', 'check_mark_button', 'sparkles', 'partying_face']),
]

# ---------- timeline ----------
t = 0.0
for it in ITEMS:
    kind = it.get('kind', 'item')
    pre = 0.9 if kind == 'intro' else 0.3
    post = 1.6 if kind == 'outro' else 0.45
    it['narr'] = lines[it['key']]
    it['start'] = t; it['pre'] = pre
    it['dur'] = pre + it['narr']['dur'] + post
    t += it['dur']
TOTAL = t
WIPE = 0.36
NFRAMES = int(math.ceil(TOTAL * FPS))

# ---------- helpers ----------
def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out_cubic(p): p = clamp(p); return 1 - (1-p)**3
def ease_out_back(p, s=1.70158): p = clamp(p); return 1 + (s+1)*(p-1)**3 + s*(p-1)**2
def ease_in_out(p): p = clamp(p); return p*p*(3-2*p)
def mix(c1, c2, a): return tuple(int(c1[i]*(1-a) + c2[i]*a) for i in range(3))

_fonts = {}
def font(path, size):
    k = (path, size)
    if k not in _fonts: _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]

def text_layer(txt, fpath, size, fill, pad=20, stroke=0, stroke_fill=None):
    f = font(fpath, size)
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    l, tp, r, b = d.textbbox((0, 0), txt, font=f, stroke_width=stroke)
    w, h = r - l + 2*pad, b - tp + 2*pad
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - tp), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im

def rounded_box(w, h, r, fill, shadow=True):
    pad = 60 if shadow else 0
    im = Image.new('RGBA', (w + 2*pad, h + 2*pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 16, pad + w, pad + h + 16), r, fill=(40, 30, 60, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(22))
        im.alpha_composite(sh)
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill)
    return im, pad

def paste_center(dst, layer, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01: return
    im = layer
    if abs(scale - 1.0) > 0.002:
        nw, nh = max(1, int(im.width*scale)), max(1, int(im.height*scale))
        im = im.resize((nw, nh), Image.BILINEAR if nw > 600 else Image.LANCZOS)
    if abs(rot) > 0.1:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.995:
        a = im.getchannel('A').point(lambda v: int(v*alpha)); im = im.copy(); im.putalpha(a)
    dst.alpha_composite(im, (int(cx - im.width/2), int(cy - im.height/2)))

def load_hero(name, maxw=860, maxh=700):
    im = Image.open(f'{A}/undraw/{name}.png').convert('RGBA')
    s = min(maxw/im.width, maxh/im.height)
    return im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)

def load_emoji(name, size=250):
    p3 = f'{A}/f3d/{name}.png'
    pm = f'{A}/fm/{name.replace("_", "-")}.png'
    if not os.path.exists(pm): pm = f'{A}/fm/{name.replace("_", "-")}-default.png'
    p = p3 if os.path.exists(p3) else pm
    im = Image.open(p).convert('RGBA')
    return im.resize((size, size), Image.LANCZOS)

def wrap_sub(txt, maxc=13):
    if len(txt) <= maxc: return [txt]
    # prefer split after punctuation
    for i in range(min(len(txt)-1, maxc), 3, -1):
        if txt[i-1] in '、。！' and len(txt) - i <= maxc: return [txt[:i], txt[i:]]
    mid = (len(txt)+1)//2
    return [txt[:mid], txt[mid:]]

def group_chunks(chunks, maxc=20):
    groups = []
    for c in chunks:
        if groups and len(groups[-1]['text']) + len(c['text']) <= maxc:
            groups[-1]['text'] += c['text']; groups[-1]['end'] = c['end']
        else:
            groups.append(dict(text=c['text'], start=c['start'], end=c['end']))
    return groups

# ---------- scene cache ----------
class Scene:
    def __init__(self, it):
        self.it = it; self.kind = it.get('kind', 'item'); self.acc = hexrgb(it['accent'])
        acc = self.acc
        # background
        bg = Image.new('RGBA', (W, H), CREAM + (255,))
        d = ImageDraw.Draw(bg)
        if self.kind != 'item':
            for y in range(H):  # vertical gradient of accent
                d.line([(0, y), (W, y)], fill=mix(acc, mix(acc, (255, 255, 255), 0.35), y/H))
        self.bg = bg
        # decorative blobs layer (drifts)
        bl = Image.new('RGBA', (W + 200, H + 200), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bl)
        col = (255, 255, 255, 60) if self.kind != 'item' else acc + (20,)
        for (x, y, r) in [(120, 420, 260), (1000, 700, 320), (180, 1500, 300), (980, 1700, 240), (560, 1000, 520)]:
            bd.ellipse((x - r, y - r, x + r, y + r), fill=col)
        # dots grid
        dcol = (255, 255, 255, 50) if self.kind != 'item' else acc + (46,)
        for gx in range(60, W + 200, 90):
            for gy in range(60, H + 200, 90):
                bd.ellipse((gx - 5, gy - 5, gx + 5, gy + 5), fill=dcol)
        self.blobs = bl
        # number badge
        if self.kind == 'item':
            b = Image.new('RGBA', (260, 260), (0, 0, 0, 0))
            ImageDraw.Draw(b).ellipse((10, 10, 250, 250), fill=acc)
            ImageDraw.Draw(b).ellipse((10, 10, 250, 250), outline=(255, 255, 255), width=8)
            num = text_layer(f'{it["num"]:02d}', FONT_NUM, 96, (255, 255, 255), pad=4)
            b.alpha_composite(num, (130 - num.width//2, 130 - num.height//2 + 2))
            self.badge = b
            self.kicker = text_layer('30代でやっておくべきこと', FONT_KICK, 40, acc, pad=8)
        # title lines
        tcol = INK if self.kind == 'item' else (255, 255, 255)
        tsize = 104 if self.kind == 'item' else 100
        self.titles = []
        for ln in it['title']:
            tl = text_layer(ln, FONT_TITLE, tsize, tcol, pad=24, stroke=(0 if self.kind == 'item' else 10), stroke_fill=mix(acc, (0, 0, 0), 0.25))
            if self.kind == 'item':
                # marker highlight under text
                mk = Image.new('RGBA', tl.size, (0, 0, 0, 0))
                ImageDraw.Draw(mk).rounded_rectangle((18, tl.height - 62, tl.width - 18, tl.height - 22), 14, fill=acc + (120,))
                mk.alpha_composite(tl); tl = mk
            self.titles.append(tl)
        if self.kind == 'intro':
            self.big = text_layer('10選', FONT_NUM, 230, (255, 255, 255), pad=30, stroke=14, stroke_fill=mix(acc, (0, 0, 0), 0.3))
        # hero card
        self.card, self.cpad = rounded_box(940, 820, 48, (255, 255, 255, 255))
        self.heroes = [load_hero(h) for h in it['heroes']]
        self.emojis = [load_emoji(e) for e in it['emojis']]
        # subtitles
        self.groups = group_chunks(it['narr']['chunks'])
        for g in self.groups:
            ls = wrap_sub(g['text'])
            layers = [text_layer(l, FONT_SUB, 62, (255, 255, 255), pad=6) for l in ls]
            tw = max(l.width for l in layers); th = sum(l.height for l in layers) + 8*(len(layers)-1)
            box, bpad = rounded_box(tw + 90, th + 56, 34, (38, 38, 52, 236), shadow=True)
            y = bpad + 28
            for l in layers:
                box.alpha_composite(l, (bpad + (tw + 90 - l.width)//2, y)); y += l.height + 8
            # accent bar on left
            ImageDraw.Draw(box).rounded_rectangle((bpad + 18, bpad + 30, bpad + 30, bpad + th + 26), 6, fill=acc)
            g['layer'] = box
        self.credit = text_layer('ナレーション：VOICEVOX：四国めたん', FONT_KICK, 28, (120, 120, 135) if self.kind == 'item' else (255, 255, 255), pad=6)
        if self.kind == 'outro':
            self.cta = text_layer('保存して、あとで見返そう', FONT_KICK, 46, (255, 255, 255), pad=10)
            self.cta_box, self.cta_pad = rounded_box(self.cta.width + 60, self.cta.height + 30, 40, mix(self.acc, (0, 0, 0), 0.35) + (255,), shadow=False)

    def render(self, tl, frame):
        """tl: local time in seconds. returns RGBA frame."""
        it = self.it; acc = self.acc; dur = it['dur']; pre = it['pre']
        img = self.bg.copy()
        dx = int(-100 + 40*math.sin(tl*0.5)); dy = int(-100 + 30*math.cos(tl*0.4))
        img.alpha_composite(self.blobs, (dx, dy))
        # progress bar
        d = ImageDraw.Draw(img)
        idx = it.get('num', 0 if self.kind == 'intro' else 10)
        prog = (idx - 1 + clamp(tl/dur)) / 10 if self.kind == 'item' else (0 if self.kind == 'intro' else 1)
        d.rounded_rectangle((60, 40, W - 60, 52), 6, fill=(255, 255, 255, 170) if self.kind != 'item' else (225, 222, 215, 255))
        if prog > 0:
            d.rounded_rectangle((60, 40, 60 + int((W - 120)*prog), 52), 6, fill=(255, 255, 255, 255) if self.kind != 'item' else acc)
        # ----- header -----
        if self.kind == 'item':
            p = ease_out_back((tl - 0.0)/0.28)
            paste_center(img, self.badge, 150, 215, scale=p)
            a = ease_out_cubic((tl - 0.06)/0.3)
            paste_center(img, self.kicker, 150 + 130 + self.kicker.width/2, 215, alpha=a)
            for i, tlr in enumerate(self.titles):
                a = ease_out_cubic((tl - 0.1 - i*0.08)/0.32)
                paste_center(img, tlr, W/2, 425 + i*110 + (1-a)*40, alpha=a)
        elif self.kind == 'intro':
            for i, tlr in enumerate(self.titles):
                a = ease_out_back((tl - 0.05 - i*0.12)/0.4)
                paste_center(img, tlr, W/2, 200 + i*118, scale=0.6 + 0.4*a, alpha=clamp(a*1.5))
            a = ease_out_back((tl - 0.38)/0.42)
            wob = 1 + 0.03*math.sin(tl*6)
            paste_center(img, self.big, W/2, 530, scale=max(0, a)*wob, alpha=clamp(a*2), rot=-6)
        else:
            for i, tlr in enumerate(self.titles):
                a = ease_out_back((tl - 0.05 - i*0.12)/0.4)
                paste_center(img, tlr, W/2, 240 + i*125, scale=0.6 + 0.4*a, alpha=clamp(a*1.5))
        # ----- hero card -----
        cy = 1060 if self.kind == 'item' else 1090
        pc = ease_out_back((tl - 0.14)/0.38)
        if pc > 0.01:
            s = max(0.01, pc)
            bob = 6*math.sin(tl*1.6)
            paste_center(img, self.card, W/2, cy + bob, scale=s)
            # which hero
            half = dur*0.52
            hi = 0 if tl < half else 1
            hero = self.heroes[hi]
            if hi == 0:
                hs = 1.0 + 0.06*clamp(tl/half)
            else:
                hp = ease_out_back((tl - half)/0.3)
                hs = (0.8 + 0.2*hp)*(1.0 + 0.05*clamp((tl-half)/(dur-half)))
            paste_center(img, hero, W/2, cy + bob, scale=s*hs, alpha=1.0 if hi == 0 else clamp((tl-half)/0.12))
        # ----- emojis -----
        pos = [(130, 680), (950, 650), (120, 1460), (960, 1470)] if self.kind == 'item' else [(130, 710), (950, 690), (120, 1490), (960, 1500)]
        for i, (em, (ex, ey)) in enumerate(zip(self.emojis, pos)):
            t0 = 0.42 + i*0.11
            pe = ease_out_back((tl - t0)/0.34)
            if pe <= 0.01: continue
            fl = 10*math.sin(tl*2.2 + i*1.7)
            rot = 8*math.sin(tl*1.3 + i) * (1 if i % 2 else -1)
            paste_center(img, em, ex, ey + fl, scale=pe*(1.0 if i % 2 else 1.08), rot=rot)
        # ----- subtitles -----
        tn = tl - pre
        for g in self.groups:
            if g['start'] - 0.05 <= tn < g['end'] + 0.22:
                ps = ease_out_back((tn - g['start'] + 0.05)/0.16)
                paste_center(img, g['layer'], W/2, 1672, scale=0.85 + 0.15*ps)
                break
        if self.kind == 'outro' and tl > pre + it['narr']['dur'] + 0.1:
            a = ease_out_back((tl - pre - it['narr']['dur'] - 0.1)/0.3)
            paste_center(img, self.cta_box, W/2, 1672, scale=a)
            paste_center(img, self.cta, W/2, 1672, scale=a)
        # credit
        img.alpha_composite(self.credit, (W//2 - self.credit.width//2, 1848))
        return img

SCENES = None
def _init():
    global SCENES
    SCENES = [Scene(it) for it in ITEMS]

def render_frame(fi):
    t = fi / FPS
    # find active scene
    si = 0
    for i, it in enumerate(ITEMS):
        if t >= it['start']: si = i
    it = ITEMS[si]
    img = SCENES[si].render(t - it['start'], fi)
    # wipe transition around boundaries
    for j, nx in enumerate(ITEMS[1:], start=1):
        b = nx['start']
        if b - WIPE/2 <= t < b + WIPE/2:
            col = hexrgb(nx['accent'])
            panel = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            pd = ImageDraw.Draw(panel)
            if t < b:
                p = ease_in_out((t - (b - WIPE/2))/(WIPE/2))  # slide in from right
                x0 = W - int((W + 160)*p)
                pd.polygon([(x0 + 160, 0), (W, 0), (W, H), (x0, H)], fill=col + (255,))
            else:
                p = ease_in_out((t - b)/(WIPE/2))  # slide out to left
                x1 = W - int((W + 160)*p)
                pd.polygon([(0, 0), (x1 + 160, 0), (x1, H), (0, H)], fill=col + (255,))
            img.alpha_composite(panel)
            break
    return img.convert('RGB')

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'render'
    if mode == 'preview':
        _init()
        times = [float(x) for x in sys.argv[2:]]
        for tt in times:
            fr = render_frame(int(tt*FPS))
            fr.save(f'{S}/preview/f_{tt:06.2f}.png')
        print('ok', TOTAL)
        return
    if mode == 'timeline':
        for it in ITEMS: print(it['key'], round(it['start'], 2), round(it['dur'], 2))
        print('TOTAL', round(TOTAL, 2), 'frames', NFRAMES); return
    out = sys.argv[2]
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=_init) as pool:
        for i, fr in enumerate(pool.imap(render_frame, range(NFRAMES), chunksize=8)):
            proc.stdin.write(fr.tobytes())
            if i % 300 == 0: print('frame', i, '/', NFRAMES, flush=True)
    proc.stdin.close(); proc.wait()
    print('video done', out, 'total', TOTAL)

if __name__ == '__main__':
    main()
