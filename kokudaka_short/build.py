"""石高ショート動画ビルダー
VOICEVOX(四国めたん)で音声を作り、PILでフレームを描いてffmpegで動画にする。
使い方: VOICEVOXエンジンを localhost:50021 で起動してから `python3 build.py`
"""
import io, json, math, subprocess, urllib.parse, urllib.request, wave
from PIL import Image, ImageDraw, ImageFont
from script import LINES

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

# ---------------- 音声 ----------------
def synth(text):
    q = urllib.parse.quote(text)
    req = urllib.request.Request(f"{ENGINE}/audio_query?speaker={SPEAKER}&text={q}", method="POST")
    query = json.load(urllib.request.urlopen(req))
    query.update(speedScale=1.18, intonationScale=1.15, pitchScale=0.0,
                 prePhonemeLength=0.05, postPhonemeLength=0.08)
    req = urllib.request.Request(f"{ENGINE}/synthesis?speaker={SPEAKER}",
                                 data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).read()

def build_audio_with_pcm():
    START, GAP, SCENE_GAP, TAIL = 0.35, 0.18, 0.45, 1.2
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
    stroke = int(stroke * min(1, size / 60)) if size < 60 else stroke
    d.multiline_text(xy, s, font=F(size, bold), fill=fill, anchor=anchor, align="center",
                     stroke_width=stroke, stroke_fill=stroke_fill, spacing=spacing)

def faded(frame, alpha, draw_fn):
    """alpha<1 の要素は別レイヤに描いて合成する"""
    if alpha <= 0: return
    if alpha >= 1:
        draw_fn(ImageDraw.Draw(frame)); return
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    a = layer.getchannel("A").point(lambda v: int(v * alpha))
    layer.putalpha(a)
    frame.alpha_composite(layer)

def chip(d, cx, cy, label, size=64, fill=GOLD, fg=INK, padx=36, pady=18):
    if size < 4: return
    f = F(size)
    l, t, r, b = d.textbbox((0, 0), label, font=f, anchor="lt")
    w, h = r - l + padx * 2, b - t + pady * 2
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

# ---------------- 背景 ----------------
def make_bg():
    bg = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(bg)
    top, bot = (28, 30, 66), (52, 26, 58)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
    # 青海波っぽい薄い模様
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
    # ヘッダ
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, W, 250), fill=(15, 14, 35, 255))
    d.rectangle((0, 250, W, 258), fill=GOLD)
    text(d, (W / 2, 95), "石高で見る", 48, fill=GOLD, bold=True)
    text(d, (W / 2, 172), "江戸の意外な真実", 84, fill=WHITE)
    text(d, (W - 30, 290), "VOICEVOX:四国めたん", 30, fill=DIM, anchor="rm", bold=True)
    return bg

# ---------------- シーン ----------------
SUB_Y = 1470  # 字幕の中心
RANK = [("加賀", 102), ("薩摩", 73), ("仙台", 62), ("尾張", 62), ("紀州", 55),
        ("熊本", 54), ("福岡", 47), ("広島", 43), ("長州", 37)]

def scene_hook(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.5))
    text(d, (W / 2, 470), "江戸時代の", 70 * max(p, 0.01), fill=CREAM)
    text(d, (W / 2, 590), "お金持ち大名", 120 * max(p, 0.01), fill=WHITE, stroke=6)
    q = ease_back(prog(st, 0.5, 0.5))
    if q > 0:
        pulse = 1 + 0.05 * math.sin(st * 6)
        r = 190 * q * pulse
        d.ellipse((W / 2 - r, 900 - r, W / 2 + r, 900 + r), fill=GOLD)
        text(d, (W / 2, 900), "No.1は？", 92 * q * pulse, fill=INK)

def scene_kaga(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.45))
    text(d, (W / 2, 400), "加賀藩", 110 * max(p, 0.01), fill=GOLD, stroke=5)
    # 102万石カウントアップ
    n = int(round(102 * ease_out(prog(st, 0.5, 1.3))))
    num_unit(d, W / 2, 680, f"{n}", "万石", 230, 90)
    if n == 102:
        a = prog(st, 1.8, 0.3)
        faded(fr, a, lambda dd: chip(dd, W / 2, 790, "大名ランキング 1位", 50, fill=RED, fg=WHITE))
    if li == 1:  # 1石＝1人1年分
        a = ease_out(prog(lt, 0, 0.35))
        def f(dd):
            text(dd, (W / 2, 950), "1石", 110, fill=GOLD, stroke=5)
            text(dd, (W / 2, 1080), "＝ 大人1人の1年分のお米", 62, fill=WHITE, stroke=4)
        faded(fr, a, f)
    elif li == 2:  # 人のグリッド
        cols, rows, s = 10, 4, 70
        x0, y0 = W / 2 - (cols - 1) * 92 / 2, 920
        k = ease_out(prog(lt, 0, 1.4)) * cols * rows
        for i in range(cols * rows):
            if i < k:
                person(d, x0 + (i % cols) * 92, y0 + (i // cols) * 78, s, GOLD if i % 7 else CREAM)
        a = prog(lt, 1.2, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1270), "約100万人を養える！", 66, fill=WHITE, stroke=5))
    elif li == 3:  # 石川＋富山
        p1, p2 = ease_back(prog(lt, 0, 0.4)), ease_back(prog(lt, 1.2, 0.4))
        if p1 > 0: chip(d, W / 2 - 240, 1010, "石川県", 76 * p1)
        if p2 > 0:
            text(d, (W / 2, 1010), "＋", 90 * p2, fill=WHITE)
            chip(d, W / 2 + 240, 1010, "富山県", 76 * p2, fill=RED, fg=WHITE)
        a = prog(lt, 1.5, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1150), "（加賀・能登・越中）", 48, fill=DIM, bold=True))

def scene_choshu(fr, d, st, li, lt):
    top, rowh, x0, scale = 340, 88, 230, 6.6
    for i, (name, v) in enumerate(RANK):
        y = top + i * rowh
        grow = ease_out(prog(st, i * 0.06, 0.6))
        hl = name == "長州"
        col = RED if hl else (110, 110, 160)
        if hl and li >= 1:  # 実力バー
            g = ease_out(prog(lt if li == 1 else 9, 0.8, 1.2))
            real = 37 + (90 - 37) * g
            d.rounded_rectangle((x0, y + 8, x0 + real * scale, y + rowh - 8), radius=12,
                                fill=(240, 190, 80, 90), outline=GOLD, width=4)
            if g > 0.98:
                text(d, (x0 + 90 * scale + 16, y + rowh / 2), "90万+", 40, fill=GOLD, anchor="lm", bold=True)
                text(d, (W / 2, top + 9 * rowh + 60), "実力は 90万石以上？", 64, fill=GOLD, stroke=5)
        d.rounded_rectangle((x0, y + 8, x0 + max(v * scale * grow, 24), y + rowh - 8), radius=12, fill=col)
        text(d, (x0 - 24, y + rowh / 2), f"{i + 1}位 {name}", 44, fill=WHITE if hl else CREAM,
             anchor="rm", bold=not hl)
        if grow > 0.9:
            text(d, (x0 + v * scale * grow + 16, y + rowh / 2), f"{v}万", 40,
                 fill=WHITE if hl else DIM, anchor="lm", bold=True, stroke=3)
    if li == 2:
        p = ease_back(prog(lt, 0.2, 0.45))
        if p > 0:
            d.rounded_rectangle((W / 2 - 330 * p, 1315 - 55 * p, W / 2 + 330 * p, 1315 + 55 * p),
                                radius=20, fill=RED)
            text(d, (W / 2, 1315), "→ 倒幕の原動力に", 70 * p, fill=WHITE)

def scene_matsumae(fr, d, st, li, lt):
    if li == 0:
        n = int(round(102 * (1 - ease_out(prog(st, 0.2, 1.2)))))
        shake = 10 * math.sin(st * 60) * clamp(1.6 - st) if n == 0 else 0
        text(d, (W / 2, 450), "石高", 80, fill=CREAM)
        num_unit(d, W / 2 + shake, 830, f"{n}", "石", 330, 110, fill=RED if n == 0 else WHITE, stroke=10)
    else:
        text(d, (W / 2, 420), "石高 0 の大名", 64, fill=RED, stroke=4)
        p = ease_back(prog(st if li == 1 else 9, 0, 0.45))
        text(d, (W / 2, 590), "松前藩", 150 * max(p, 0.01), fill=GOLD, stroke=6)
        text(d, (W / 2, 740), "（北海道）", 60, fill=CREAM, bold=True)
        if li == 2:
            for k, (lab, x, col) in enumerate([("昆布", W / 2 - 300, (70, 150, 110)),
                                              ("鮭", W / 2, RED),
                                              ("交易", W / 2 + 300, GOLD)]):
                q = ease_back(prog(lt, 0.3 + k * 0.6, 0.4))
                if q > 0:
                    chip(d, x, 960, lab, 80 * q, fill=col, fg=WHITE if col != GOLD else INK)
            a = prog(lt, 2.0, 0.3)
            faded(fr, a, lambda dd: text(dd, (W / 2, 1120), "お米の代わりに海の幸で稼いだ", 52,
                                         fill=WHITE, stroke=4))

def scene_outro(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.5))
    text(d, (W / 2, 520), "石高で見ると", 90 * max(p, 0.01), fill=CREAM)
    text(d, (W / 2, 680), "地図が変わる", 130 * max(p, 0.01), fill=GOLD, stroke=6)
    if li == 1:
        q = ease_back(prog(lt, 0, 0.45))
        if q > 0:
            d.rounded_rectangle((W / 2 - 400 * q, 960 - 110 * q, W / 2 + 400 * q, 960 + 110 * q),
                                radius=40, fill=WHITE)
            d.polygon([(W / 2 - 60 * q, 960 + 105 * q), (W / 2 + 10 * q, 960 + 105 * q),
                       (W / 2 - 90 * q, 960 + 170 * q)], fill=WHITE)
            text(d, (W / 2, 925), "次はどの藩が知りたい？", 56 * q, fill=INK)
            text(d, (W / 2, 1010), "コメントで教えてね！", 56 * q, fill=RED)

SCENES = dict(hook=scene_hook, kaga=scene_kaga, choshu=scene_choshu,
              matsumae=scene_matsumae, outro=scene_outro)

def subtitle(fr, d, item, t):
    a = ease_out(prog(t, item["start"] - 0.05, 0.18))
    dy = 20 * (1 - a)
    lines = item["sub"].split("\n")
    size = 66 if max(len(l) for l in lines) <= 13 else 58
    faded(fr, a, lambda dd: text(dd, (W / 2, SUB_Y + dy), item["sub"], size, fill=WHITE,
                                 stroke=9, stroke_fill=(10, 10, 20), spacing=20))

# ---------------- 本体 ----------------
def main():
    print("音声を合成中…")
    timeline, total = build_audio_with_pcm()
    # シーンの開始時刻と、行ごとの表示区間（次の行が始まるまで表示）
    scene_start = {}
    for item in timeline:
        scene_start.setdefault(item["scene"], item["start"] - 0.2)
    for i, item in enumerate(timeline):
        item["show_until"] = timeline[i + 1]["start"] - 0.05 if i + 1 < len(timeline) else total
        item["idx_in_scene"] = sum(1 for x in timeline[:i] if x["scene"] == item["scene"])
    bg = make_bg()
    nframes = int(total * FPS)
    print(f"映像を描画中… {total:.1f}秒 / {nframes}フレーム")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", "narration.wav",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
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
            subtitle(fr, ImageDraw.Draw(fr), cur, t)
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % 300 == 0: print(f"  {fi}/{nframes}")
    ff.stdin.close(); ff.wait()
    print("完成:", OUT)

if __name__ == "__main__":
    main()
