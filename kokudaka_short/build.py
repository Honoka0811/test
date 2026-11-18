"""石高ショート動画ビルダー
VOICEVOX(四国めたん)で音声を作り、PILでフレームを描き、オリジナルBGM・効果音を重ねて
ffmpegで縦型動画にする。
使い方: VOICEVOXエンジンを localhost:50021 で起動してから `python3 build.py`
"""
import io, json, math, subprocess, urllib.parse, urllib.request, wave
from PIL import Image, ImageDraw, ImageFont
from script import LINES
import bgm

W, H, FPS = 1080, 1920, 30
SPEAKER = 2  # 四国めたん ノーマル
ENGINE = "http://localhost:50021"
OUT = "kokudaka_short.mp4"
FONT_BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

GOLD = (240, 190, 80)
RED = (225, 70, 60)
WHITE = (255, 255, 255)
CREAM = (250, 240, 220)
DIM = (170, 170, 200)
INK = (20, 18, 40)
GREEN = (70, 150, 110)
BROWN = (130, 80, 45)

# ---------------- 音声 ----------------
def synth(text):
    q = urllib.parse.quote(text)
    req = urllib.request.Request(f"{ENGINE}/audio_query?speaker={SPEAKER}&text={q}", method="POST")
    query = json.load(urllib.request.urlopen(req))
    query.update(speedScale=1.2, intonationScale=1.2, pitchScale=0.0,
                 prePhonemeLength=0.05, postPhonemeLength=0.08, outputSamplingRate=48000)
    req = urllib.request.Request(f"{ENGINE}/synthesis?speaker={SPEAKER}",
                                 data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).read()

def build_narration():
    START, GAP, SCENE_GAP, TAIL = 0.6, 0.15, 0.4, 1.8
    clips, rate = [], None
    for line in LINES:
        with wave.open(io.BytesIO(synth(line["say"]))) as w:
            rate = rate or w.getframerate()
            clips.append(w.readframes(w.getnframes()))
    timeline, t, prev = [], START, None
    for line, pcm in zip(LINES, clips):
        if prev is not None:
            t += SCENE_GAP if line["scene"] != prev else GAP
        dur = len(pcm) / 2 / rate
        timeline.append(dict(line, start=t, end=t + dur, pcm=pcm))
        t += dur
        prev = line["scene"]
    total = t + TAIL
    buf = bytearray(int(total * rate) * 2)
    for item in timeline:
        off = int(item["start"] * rate) * 2
        buf[off:off + len(item["pcm"])] = item["pcm"]
        print(f"  {item['start']:5.2f}-{item['end']:5.2f}s  {item['say']}")
    with wave.open("narration.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(bytes(buf))
    return timeline, total

# ---------------- 描画ヘルパ ----------------
_fonts = {}
def F(size, bold=False):
    key = (int(size), bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_BLACK, int(size), index=0)
    return _fonts[key]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x):
    x = clamp(x); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def prog(t, start, dur): return clamp((t - start) / dur)

def text(d, xy, s, size, fill=WHITE, anchor="mm", stroke=0, stroke_fill=INK, bold=False, spacing=12):
    if size < 4: return
    if size < 60: stroke = int(stroke * size / 60)
    d.multiline_text(xy, s, font=F(size, bold), fill=fill, anchor=anchor, align="center",
                     stroke_width=stroke, stroke_fill=stroke_fill, spacing=spacing)

def faded(frame, alpha, draw_fn):
    if alpha <= 0: return
    if alpha >= 1:
        draw_fn(ImageDraw.Draw(frame)); return
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(layer)

def chip(d, cx, cy, label, size=64, fill=GOLD, fg=INK, padx=36, pady=18):
    if size < 4: return
    f = F(size)
    l, t, r, b = d.textbbox((0, 0), label, font=f, anchor="lt")
    k = size / 64
    w, h = r - l + padx * 2 * k, b - t + pady * 2 * k
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=h / 2, fill=fill)
    text(d, (cx, cy), label, size, fill=fg)

def num_unit(d, cx, y, num, unit, nsize, usize, fill=WHITE, stroke=8):
    fn, fu = F(nsize), F(usize)
    wn = d.textlength(num, font=fn); wu = d.textlength(unit, font=fu); gap = 12
    x = cx - (wn + gap + wu) / 2
    d.text((x, y), num, font=fn, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=INK)
    d.text((x + wn + gap, y), unit, font=fu, fill=WHITE, anchor="ls", stroke_width=6, stroke_fill=INK)

def person(d, cx, cy, s, fill):
    d.ellipse((cx - s * 0.22, cy - s * 0.5, cx + s * 0.22, cy - s * 0.06), fill=fill)
    d.rounded_rectangle((cx - s * 0.34, cy, cx + s * 0.34, cy + s * 0.5), radius=s * 0.18, fill=fill)

def koban(d, cx, cy, s):  # 小判
    d.ellipse((cx - s, cy - s * 0.62, cx + s, cy + s * 0.62), fill=GOLD, outline=(170, 120, 30), width=4)
    d.ellipse((cx - s * 0.7, cy - s * 0.4, cx + s * 0.7, cy + s * 0.4), outline=(200, 150, 50), width=3)

def rice_sack(d, cx, cy, s):  # 米俵
    d.rounded_rectangle((cx - s, cy - s * 0.62, cx + s, cy + s * 0.62), radius=s * 0.5,
                        fill=(225, 200, 140), outline=(150, 115, 60), width=5)
    for k in (-0.55, 0.55):
        d.line((cx + s * k, cy - s * 0.6, cx + s * k, cy + s * 0.6), fill=(150, 115, 60), width=8)
    text(d, (cx, cy), "米", int(s * 0.7), fill=(120, 80, 40))

def bowl_crossed(d, cx, cy, s):  # ご飯茶碗に×
    d.pieslice((cx - s, cy - s, cx + s, cy + s), 0, 180, fill=(200, 80, 60))
    d.ellipse((cx - s * 0.95, cy - s * 0.55, cx + s * 0.95, cy + s * 0.25), fill=WHITE)
    w = int(s * 0.22)
    d.line((cx - s * 1.1, cy - s * 0.9, cx + s * 1.1, cy + s * 1.0), fill=RED, width=w)
    d.line((cx + s * 1.1, cy - s * 0.9, cx - s * 1.1, cy + s * 1.0), fill=RED, width=w)

def wallet(d, cx, cy, s, open_k=1.0):  # 隠し財布
    for i in range(3):  # はみ出す小判
        koban(d, cx - s * 0.5 + i * s * 0.5, cy - s * 0.55 - open_k * s * 0.25, s * 0.32)
    d.rounded_rectangle((cx - s, cy - s * 0.6, cx + s, cy + s * 0.6), radius=s * 0.18, fill=BROWN,
                        outline=(80, 45, 20), width=6)
    d.rounded_rectangle((cx - s, cy - s * 0.6, cx + s, cy - s * 0.05), radius=s * 0.18,
                        fill=(150, 95, 55), outline=(80, 45, 20), width=6)
    d.ellipse((cx - s * 0.12, cy - s * 0.17, cx + s * 0.12, cy + s * 0.07), fill=GOLD)

def stamp(frame, cx, cy, label, k):
    """ドンと押されるハンコ（kは0→1、大きい→等倍へ）"""
    if k <= 0: return
    size = 120
    f = F(size)
    tw = int(ImageDraw.Draw(frame).textlength(label, font=f))
    lw, lh = tw + 120, size + 110
    layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((8, 8, lw - 8, lh - 8), radius=26, outline=RED, width=14, fill=(255, 250, 240, 235))
    ld.text((lw / 2, lh / 2), label, font=f, fill=RED, anchor="mm")
    scale = 1 + 1.4 * (1 - ease_out(k))
    layer = layer.resize((int(lw * scale), int(lh * scale)))
    layer = layer.rotate(-10, expand=True, resample=Image.BICUBIC)
    alpha = clamp(k * 3)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

# ---------------- 背景 ----------------
def make_bg():
    bg = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(bg)
    top, bot = (28, 30, 66), (52, 26, 58)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
    pat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pat)
    r = 70
    for row, y in enumerate(range(-r, H + r, r // 2)):
        off = (row % 2) * r
        for x in range(-r, W + 2 * r, 2 * r):
            for k in (1.0, 0.72, 0.44):
                pd.ellipse((x + off - r * k, y - r * k, x + off + r * k, y + r * k),
                           outline=(255, 255, 255, 10), width=3)
    bg.alpha_composite(pat)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, W, 250), fill=(15, 14, 35, 255))
    d.rectangle((0, 250, W, 258), fill=GOLD)
    text(d, (W / 2, 95), "石高で見る", 48, fill=GOLD, bold=True)
    text(d, (W / 2, 172), "江戸の意外な真実", 84, fill=WHITE)
    text(d, (W - 30, 290), "VOICEVOX:四国めたん", 30, fill=DIM, anchor="rm", bold=True)
    return bg

# ---------------- シーン ----------------
# 各関数: (frame, draw, シーン内時刻, シーン内の行番号, 行内時刻)
SUB_Y = 1470

def scene_hook(fr, d, st, li, lt):
    n = int(round(102 * (1 - ease_out(prog(st, 0.1, 1.0)))))
    shake = 12 * math.sin(st * 60) * clamp(1.5 - st) if n == 0 else 0
    text(d, (W / 2, 440), "石高", 90, fill=CREAM)
    num_unit(d, W / 2 + shake, 860, f"{n}", "石", 380, 120, fill=RED if n == 0 else WHITE, stroke=10)
    p = ease_back(prog(st, 1.3, 0.45))
    chip(d, W / 2, 1060, "なのに大名！？", 84 * p, fill=GOLD)

def snow(d, st, n=40):
    for i in range(n):
        x = (i * 137.5) % W + 30 * math.sin(st * 1.5 + i)
        y = 280 + ((i * 263 + st * (90 + (i % 5) * 25)) % 1000)
        r = 5 + (i % 4) * 3
        d.ellipse((x - r, y - r, x + r, y + r), fill=(235, 240, 255))

def scene_matsumae(fr, d, st, li, lt):
    snow(d, st)
    p = ease_back(prog(st, 0, 0.45))
    text(d, (W / 2, 420), "松前藩", 150 * max(p, 0.01), fill=GOLD, stroke=6)
    text(d, (W / 2, 560), "（いまの北海道）", 56, fill=CREAM, bold=True)
    if li == 0:
        q = ease_back(prog(lt, 1.0, 0.45))
        if q > 0: bowl_crossed(d, W / 2, 860, 170 * q)
    else:
        items = [("交易", W / 2 - 300, GOLD, INK, 1.2), ("昆布", W / 2, GREEN, WHITE, 2.2), ("鮭", W / 2 + 300, RED, WHITE, 2.8)]
        for lab, x, col, fg, at in items:
            q = ease_back(prog(lt, at, 0.4))
            chip(d, x, 800, lab, 84 * q, fill=col, fg=fg)
        q = ease_back(prog(lt, 3.8, 0.45))
        if q > 0:
            text(d, (W / 2, 950), "↓", 90 * q, fill=WHITE)
            text(d, (W / 2, 1110), "お米ゼロでも稼げた！", 80 * q, fill=GOLD, stroke=6)

def scene_scale(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.45))
        text(d, (W / 2, 450), "石高とは？", 110 * max(p, 0.01), fill=WHITE, stroke=5)
        q = ease_back(prog(lt, 0.6, 0.45))
        if q > 0: rice_sack(d, W / 2, 800, 220 * q)
        a = prog(lt, 1.2, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1110), "＝ とれるお米の量", 76, fill=GOLD, stroke=5))
    elif li == 1:
        rice_sack(d, W / 2 - 250, 520, 150)
        text(d, (W / 2 + 170, 470), "1石", 120, fill=GOLD, stroke=5)
        text(d, (W / 2 + 170, 590), "約150kg", 56, fill=CREAM, bold=True)
        q = ease_back(prog(lt, 1.0, 0.4))
        if q > 0:
            person(d, W / 2 - 120, 800, 120 * q, CREAM)
            text(d, (W / 2 + 120, 810), "1人の1年分", 64 * q, fill=WHITE, stroke=4)
        q = ease_back(prog(lt, 3.2, 0.45))
        if q > 0:
            d.rounded_rectangle((W / 2 - 420 * q, 1040 - 95 * q, W / 2 + 420 * q, 1040 + 95 * q),
                                radius=30, fill=RED)
            text(d, (W / 2, 1040), "今なら 数万〜10万円", 70 * q, fill=WHITE)
    else:
        text(d, (W / 2, 400), "加賀藩", 100, fill=GOLD, stroke=5)
        n = int(round(102 * ease_out(prog(lt, 0.1, 1.2))))
        num_unit(d, W / 2, 660, f"{n}", "万石", 220, 90)
        cols, rows, s = 10, 4, 70
        x0, y0 = W / 2 - (cols - 1) * 92 / 2, 800
        k = ease_out(prog(lt, 1.6, 1.4)) * cols * rows
        for i in range(cols * rows):
            if i < k:
                person(d, x0 + (i % cols) * 92, y0 + (i // cols) * 78, s, GOLD if i % 7 else CREAM)
        a = prog(lt, 2.8, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1180), "100万人を食べさせられる国！", 66, fill=WHITE, stroke=5))

def scene_satsuma(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.45))
        text(d, (W / 2, 520), "大きい藩ほど", 90 * max(p, 0.01), fill=CREAM)
        q = ease_back(prog(lt, 0.7, 0.45))
        if q > 0:
            text(d, (W / 2, 730), "財政は", 90 * q, fill=WHITE)
            text(d, (W / 2, 920), "火の車", 190 * q, fill=(255, 120, 50), stroke=8)
        return
    text(d, (W / 2, 380), "薩摩藩（77万石）", 72, fill=GOLD, stroke=4)
    if li == 1:
        # 小判が積み上がる
        k = ease_out(prog(lt, 1.8, 2.0))
        pile = [(x, y) for y in range(5) for x in range(7 - y)]
        for i, (x, y) in enumerate(pile):
            if i < k * len(pile):
                cx = W / 2 + (x - (6 - y) / 2) * 120
                koban(d, cx, 1090 - y * 66, 54)
        n = int(round(500 * ease_out(prog(lt, 2.4, 1.4))))
        text(d, (W / 2, 470), "借金", 64, fill=CREAM, bold=True)
        num_unit(d, W / 2, 700, f"{n}", "万両", 200, 90, fill=RED)
        a = ease_back(prog(lt, 4.4, 0.45))
        chip(d, W / 2, 1250, "今なら数千億円！？", 70 * a, fill=RED, fg=WHITE)
    else:
        q = ease_back(prog(lt if li == 2 else 9, 1.4, 0.4))
        chip(d, W / 2, 560, "無利子", 90 * q, fill=GREEN, fg=WHITE)
        n = int(round(250 * ease_out(prog(lt if li == 2 else 9, 2.0, 0.9))))
        if li == 3 or lt > 2.0:
            num_unit(d, W / 2, 900, f"{n}", "年払い", 260, 100, fill=GOLD)
        if li == 3:
            stamp(fr, W / 2, 1110, "ほぼ踏み倒し", prog(lt, 0, 0.25))

def scene_choshu(fr, d, st, li, lt):
    text(d, (W / 2, 390), "長州藩", 110, fill=GOLD, stroke=5)
    if li == 0:
        text(d, (W / 2, 540), "表向きは 37万石", 64, fill=CREAM, stroke=4)
        q = ease_back(prog(lt, 3.6, 0.5))
        if q > 0:
            wallet(d, W / 2, 860, 230 * q, open_k=0.5 + 0.5 * math.sin(st * 4))
            text(d, (W / 2, 1120), "裏の“隠し財布”", 80 * q, fill=GOLD, stroke=6)
    else:
        steps = [("隠し財布", BROWN, WHITE), ("最新の武器", (80, 90, 140), WHITE), ("幕府を倒す！", RED, WHITE)]
        for k, (lab, col, fg) in enumerate(steps):
            q = ease_back(prog(lt, (0.1, 1.1, 2.4)[k], 0.4))
            y = 580 + k * 230
            chip(d, W / 2, y, lab, 84 * q, fill=col, fg=fg)
            if k > 0 and q > 0:
                text(d, (W / 2, y - 118), "↓", 70, fill=WHITE)

def scene_outro(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.5))
    text(d, (W / 2, 450), "時代を動かしたのは", 70 * max(p, 0.01), fill=CREAM)
    q = ease_back(prog(st, 1.8, 0.45))
    if q > 0:
        text(d, (W / 2, 610), "石高", 80 * q, fill=DIM)
        d.line((W / 2 - 100 * q, 610, W / 2 + 100 * q, 610), fill=RED, width=10)
    r = ease_back(prog(st, 2.6, 0.5))
    if r > 0:
        text(d, (W / 2, 790), "隠れた稼ぎ", 150 * r, fill=GOLD, stroke=8)
    if li == 1:
        q = ease_back(prog(lt, 0, 0.45))
        if q > 0:
            d.rounded_rectangle((W / 2 - 380 * q, 1060 - 100 * q, W / 2 + 380 * q, 1060 + 100 * q),
                                radius=40, fill=WHITE)
            d.polygon([(W / 2 - 60 * q, 1060 + 95 * q), (W / 2 + 10 * q, 1060 + 95 * q),
                       (W / 2 - 90 * q, 1060 + 160 * q)], fill=WHITE)
            text(d, (W / 2, 1060), "フォローで続きも！", 70 * q, fill=RED)

SCENES = dict(hook=scene_hook, matsumae=scene_matsumae, scale=scene_scale,
              satsuma=scene_satsuma, choshu=scene_choshu, outro=scene_outro)

# 効果音（行番号, 行内の秒, 種類）
LINE_SE = [(0, 1.3, "kira"), (1, 1.0, "pop"), (2, 1.2, "pop"), (2, 2.2, "pop"), (2, 2.8, "pop"),
           (2, 3.8, "kira"), (3, 0.6, "pop"), (4, 1.0, "pop"), (4, 3.2, "pop"), (5, 1.4, "kira"),
           (7, 1.8, "coin"), (7, 2.8, "coin"), (7, 4.4, "pop"), (8, 1.4, "pop"), (8, 2.9, "kira"),
           (9, 0.0, "stamp"), (10, 3.6, "coin"), (11, 0.1, "pop"), (11, 1.1, "pop"), (11, 2.4, "don"),
           (12, 2.4, "kira"), (13, 0.0, "pop")]

def subtitle(fr, item, t):
    a = ease_out(prog(t, item["start"] - 0.05, 0.18))
    dy = 20 * (1 - a)
    lines = item["sub"].split("\n")
    size = 66 if max(len(l) for l in lines) <= 13 else 58
    faded(fr, a, lambda dd: text(dd, (W / 2, SUB_Y + dy), item["sub"], size, fill=WHITE,
                                 stroke=9, stroke_fill=(10, 10, 20), spacing=20))

# ---------------- 本体 ----------------
def main():
    print("ナレーションを合成中…")
    timeline, total = build_narration()
    scene_start = {}
    for item in timeline:
        scene_start.setdefault(item["scene"], item["start"] - 0.2)
    for i, item in enumerate(timeline):
        item["show_until"] = timeline[i + 1]["start"] - 0.05 if i + 1 < len(timeline) else total
        item["idx_in_scene"] = sum(1 for x in timeline[:i] if x["scene"] == item["scene"])

    print("BGM・効果音を合成中…")
    events = [(s, "don") for name, s in scene_start.items() if name != "hook"]
    events += [(timeline[i]["start"] + off, kind) for i, off, kind in LINE_SE]
    bgm.write_wav("bgm.wav", bgm.make_bgm(total))
    bgm.write_wav("se.wav", bgm.make_se(total, events))

    bg = make_bg()
    nframes = int(total * FPS)
    print(f"映像を描画中… {total:.1f}秒 / {nframes}フレーム")
    # ナレーション中はBGMを自動で下げる（サイドチェイン）
    af = ("[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit=2[n1][n2];"
          "[2:a]volume=0.55[b0];[b0][n1]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[b];"
          "[3:a]volume=0.6[s];"
          "[n2][b][s]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[a]")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", "narration.wav", "-i", "bgm.wav", "-i", "se.wav",
                           "-filter_complex", af, "-map", "0:v", "-map", "[a]",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for fi in range(nframes):
        t = fi / FPS
        cur = timeline[0]
        for item in timeline:
            if t >= item["start"] - 0.2: cur = item
        fr = bg.copy()
        d = ImageDraw.Draw(fr)
        st = t - scene_start[cur["scene"]]
        SCENES[cur["scene"]](fr, d, st, cur["idx_in_scene"], t - cur["start"])
        if t <= cur["show_until"]:
            subtitle(fr, cur, t)
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % 300 == 0: print(f"  {fi}/{nframes}")
    ff.stdin.close(); ff.wait()
    print("完成:", OUT)

if __name__ == "__main__":
    main()
