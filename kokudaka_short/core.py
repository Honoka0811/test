"""石高ショート動画 共通エンジン
VOICEVOX(四国めたん)で音声を作り、PILでフレームを描き、オリジナルBGM・効果音を重ねて
ffmpegで縦型動画にする。
使い方: VOICEVOXエンジンを localhost:50021 で起動してから `python3 build.py`
"""
import io, json, math, subprocess, urllib.parse, urllib.request, wave
from PIL import Image, ImageDraw, ImageFont
import bgm, importlib, sys

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

def build_narration(LINES, wav_path):
    START, GAP, SCENE_GAP, TAIL, SEG_GAP = 0.6, 0.15, 0.4, 1.8, 0.12
    rate = 48000
    clips = []
    for line in LINES:
        pcm, cues = b"", []
        for k, seg in enumerate(line["say"].split("|")):
            if k: pcm += b"\0\0" * int(SEG_GAP * rate)
            cues.append(len(pcm) / 2 / rate)
            with wave.open(io.BytesIO(synth(seg))) as w:
                pcm += w.readframes(w.getnframes())
        clips.append((pcm, cues))
    timeline, t, prev = [], START, None
    for line, (pcm, cues) in zip(LINES, clips):
        if prev is not None:
            t += SCENE_GAP if line["scene"] != prev else GAP
        dur = len(pcm) / 2 / rate
        timeline.append(dict(line, start=t, end=t + dur, pcm=pcm, cues=cues))
        t += dur
        prev = line["scene"]
    total = t + TAIL
    buf = bytearray(int(total * rate) * 2)
    for item in timeline:
        off = int(item["start"] * rate) * 2
        buf[off:off + len(item["pcm"])] = item["pcm"]
        print(f"  {item['start']:5.2f}-{item['end']:5.2f}s  cues={[round(c,2) for c in item['cues']]}  {item['say']}")
    with wave.open(wav_path, "wb") as w:
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
def make_bg(badge=""):
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
    if badge:
        d.rounded_rectangle((24, 272, 24 + 40 * len(badge) + 40, 332), radius=30, fill=RED)
        text(d, (44 + 20 * len(badge), 302), badge, 36, fill=WHITE)
    text(d, (W - 30, 302), "VOICEVOX:四国めたん", 30, fill=DIM, anchor="rm", bold=True)
    return bg

SUB_Y = 1470
STATE = {}

def cue(k, add=0.0):
    """現在の行で k 番目の区切り（say の "|"）が始まる行内秒"""
    cues = STATE["cur"]["cues"]
    return cues[min(k, len(cues) - 1)] + add

def subtitle(fr, item, t):
    a = ease_out(prog(t, item["start"] - 0.05, 0.18))
    dy = 20 * (1 - a)
    lines = item["sub"].split("\n")
    size = 66 if max(len(l) for l in lines) <= 13 else 58
    faded(fr, a, lambda dd: text(dd, (W / 2, SUB_Y + dy), item["sub"], size, fill=WHITE,
                                 stroke=9, stroke_fill=(10, 10, 20), spacing=20))

# ---------------- 本体 ----------------
def render(ep):
    LINES, SCENES, LINE_SE = ep.LINES, ep.SCENES, ep.LINE_SE
    out = f"{ep.__name__}.mp4"
    print("ナレーションを合成中…")
    timeline, total = build_narration(LINES, "narration.wav")
    scene_start = {}
    for item in timeline:
        scene_start.setdefault(item["scene"], item["start"] - 0.2)
    for i, item in enumerate(timeline):
        item["show_until"] = timeline[i + 1]["start"] - 0.05 if i + 1 < len(timeline) else total
        item["idx_in_scene"] = sum(1 for x in timeline[:i] if x["scene"] == item["scene"])

    print("BGM・効果音を合成中…")
    events = [(s, "don") for name, s in scene_start.items() if name != "hook"]
    def se_time(i, off):  # off が ("c", k, 追加秒) なら k番目の区切りに合わせる
        if isinstance(off, tuple): return timeline[i]["start"] + timeline[i]["cues"][off[1]] + off[2]
        return timeline[i]["start"] + off
    events += [(se_time(i, off), kind) for i, off, kind in LINE_SE]
    music = bgm.make_bgm(total)
    import numpy as np
    gain = np.ones(len(music))
    tt = np.arange(len(music)) / bgm.SR
    for name in getattr(ep, "QUIET_SCENES", []):
        s0 = scene_start[name]
        s1 = max(x["end"] for x in timeline if x["scene"] == name) + 0.3
        ramp = np.clip(np.minimum(tt - s0, s1 - tt) / 0.6, 0, 1)
        gain = np.minimum(gain, 1 - 0.75 * ramp)
    bgm.write_wav("bgm.wav", music * gain[:, None])
    bgm.write_wav("se.wav", bgm.make_se(total, events))

    bg = make_bg(ep.BADGE)
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
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(nframes):
        t = fi / FPS
        cur = timeline[0]
        for item in timeline:
            if t >= item["start"] - 0.2: cur = item
        fr = bg.copy()
        d = ImageDraw.Draw(fr)
        st = t - scene_start[cur["scene"]]
        STATE["cur"] = cur  # シーン関数から cue() で区切り時刻を参照できるように
        SCENES[cur["scene"]](fr, d, st, cur["idx_in_scene"], t - cur["start"])
        if t <= cur["show_until"]:
            subtitle(fr, cur, t)
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % 300 == 0: print(f"  {fi}/{nframes}")
    ff.stdin.close(); ff.wait()
    print("完成:", out)

if __name__ == "__main__":
    for name in sys.argv[1:] or ["ep1", "ep2", "ep3"]:
        print(f"==== {name} ====")
        render(importlib.import_module(name))
