#!/usr/bin/env python3
"""高校卒業までに絶対やっておくべきこと10選 ショート動画ビルダー
 - ナレーション: VOICEVOX 四国めたん(ノーマル) ※tts.quest の公開 Web API 経由
 - BGM: numpy で合成(オリジナル)
 - 映像: Pillow で 1080x1920 を描画 → ffmpeg で合成
使い方: python3 build.py [出力ディレクトリ]
"""
import json, math, os, subprocess, sys, time, urllib.parse, urllib.request, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(OUT, "work")
os.makedirs(WORK, exist_ok=True)

SPEAKER = 6  # 四国めたん ツンツン
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

# (大見出し, サブ見出し, ナレーション)
INTRO = ("高校卒業までに", "やっておかないと|後悔する十選", "高校卒業までに、後悔しない十選。ありきたりなのは、省いたよ!")
# 10位 → 1位のカウントダウン順
ITEMS = [
    ("SNSの|黒歴史を消す", "就活で見られるかも",
     "十位、SNSの黒歴史を消す。就活で、見られるよ!"),
    ("友達の|口癖を録音する", "10年後、爆笑できる",
     "九位、友達の口癖を録音する。十年後、爆笑できる!"),
    ("先生の|黒歴史を聞き出す", "意外と教えてくれる",
     "八位、先生の黒歴史を聞き出す。意外と、教えてくれる!"),
    ("放課後の教室に|意味もなく居座る", "二度と戻れない時間",
     "七位、放課後の教室に居座る。二度と戻れない時間!"),
    ("一人で|知らない駅まで行く", "世界が少し広がる",
     "六位、一人で知らない駅まで行く。世界が少し広がるよ!"),
    ("契約の|怖さを知る", "18歳で成人。サブスク・リボ注意",
     "五位、契約の怖さを知る。十八歳で成人、リボ払い注意!"),
    ("親に|高校時代の話を聞く", "意外な一面が見える",
     "四位、親に高校時代の話を聞く。意外な一面が見えるよ!"),
    ("苦手だったやつと|一回ちゃんと話す", "意外といいやつかも",
     "三位、苦手だったやつと、一回話す。意外と、いいやつかも!"),
    ("10年後の自分に|動画メッセージ", "未来で泣くやつ",
     "二位、十年後の自分に、動画メッセージを撮る。未来で泣くやつ!"),
    ("卒業後の|次の約束を今決める", "日付つきで絶対",
     "一位、卒業後の次の約束を、今決める。日付つきで、絶対!"),
]
OUTRO = ("全部やれたら", "最高の卒業!", "全部やれたら、最高の卒業! 保存して、友達に送ってね!")

# 背景グラデーション (上, 下) と アクセント色
PALETTES = [
    ((255, 154, 158), (250, 208, 196), (214, 51, 108)),
    ((161, 140, 209), (251, 194, 235), (112, 72, 189)),
    ((132, 250, 176), (143, 211, 244), (16, 124, 112)),
    ((255, 236, 210), (252, 182, 159), (222, 82, 56)),
    ((166, 192, 254), (246, 128, 132), (52, 84, 209)),
    ((250, 240, 168), (176, 224, 176), (46, 125, 50)),
    ((224, 195, 252), (142, 197, 252), (84, 60, 190)),
    ((255, 204, 112), (200, 80, 192), (153, 27, 130)),
    ((254, 225, 64), (250, 112, 154), (190, 40, 90)),
    ((137, 247, 254), (102, 166, 255), (20, 80, 190)),
]


# ---------------------------------------------------------------- narration
def tts(text, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        try:
            wav_len(path)
            return
        except Exception:
            os.remove(path)
    q = urllib.parse.urlencode({"text": text, "speaker": SPEAKER})
    for attempt in range(8):
        try:
            with urllib.request.urlopen("https://api.tts.quest/v3/voicevox/synthesis?" + q, timeout=30) as r:
                j = json.load(r)
            if j.get("success"):
                break
            if j.get("retryAfter"):
                time.sleep(float(j["retryAfter"]) + 1)
                continue
            raise RuntimeError(j)
        except Exception as e:
            print("retry", attempt, e)
            time.sleep(3)
    else:
        raise RuntimeError("tts failed: " + text)
    for _ in range(40):
        with urllib.request.urlopen(j["audioStatusUrl"], timeout=30) as r:
            st = json.load(r)
        if st.get("isAudioReady"):
            break
        if st.get("isAudioError"):
            raise RuntimeError(st)
        time.sleep(1)
    for attempt in range(6):
        try:
            urllib.request.urlretrieve(j["wavDownloadUrl"], path)
            return
        except Exception as e:
            print("download retry", attempt, e)
            time.sleep(3)
    raise RuntimeError("download failed: " + text)


def wav_len(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------- drawing
def font(size):
    return ImageFont.truetype(FONT, size)


def gradient(top, bot):
    t = np.array(top, np.float32)
    b = np.array(bot, np.float32)
    k = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = (t * (1 - k) + b * k).repeat(W, axis=1)
    return Image.fromarray(img.astype(np.uint8), "RGB")


def wrap(draw, text, f, maxw):
    """幅に収まる最小の行数を求め、行ごとの文字数を均等に分割する"""
    if "|" in text:  # 手動改行位置
        return text.split("|")
    n = max(1, math.ceil(draw.textlength(text, font=f) / maxw))
    while True:
        per = math.ceil(len(text) / n)
        lines = [text[i:i + per] for i in range(0, len(text), per)]
        if all(draw.textlength(l, font=f) <= maxw for l in lines) or n >= len(text):
            return lines
        n += 1


def text_layer(lines, f, fill, stroke=0, stroke_fill=None, gap=24, shadow=None):
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ws = [d0.textlength(l, font=f) for l in lines]
    lh = f.size + gap
    w = int(max(ws)) + 120
    h = lh * len(lines) + 120
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = (w - ws[i]) / 2
        y = 60 + i * lh
        if shadow:
            d.text((x + 6, y + 8), l, font=f, fill=shadow, stroke_width=stroke, stroke_fill=shadow)
        d.text((x, y), l, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def paste_center(base, layer, cx, cy, scale=1.0, alpha=1.0, dy=0):
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    base.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2 + dy)))


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out(t):
    return 1 - (1 - t) ** 3


def deco_circles(bg, accent, seed):
    rng = np.random.default_rng(seed)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for _ in range(9):
        r = int(rng.integers(90, 260))
        x, y = int(rng.integers(-60, W + 60)), int(rng.integers(-60, H + 60))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 38))
    bg.alpha_composite(ov)


def build_scene(idx, kind, head, sub, accent, pal):
    """returns (static_bg RGBA, dict of layers)"""
    bg = gradient(pal[0], pal[1]).convert("RGBA")
    deco_circles(bg, accent, idx + 1)
    d = ImageDraw.Draw(bg)

    # 上部: 進捗バー
    if kind == "item":
        bar_x0, bar_x1, bar_y = 90, W - 90, 150
        d.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + 18), 9, fill=(255, 255, 255, 140))
        frac = (11 - idx) / 10
        d.rounded_rectangle((bar_x0, bar_y, bar_x0 + (bar_x1 - bar_x0) * frac, bar_y + 18), 9, fill=accent + (255,))
        d.text((W - 90, bar_y + 34), f"NO.{idx}", font=font(44), fill=accent + (255,), anchor="ra")
    # 下部クレジット
    d.text((W / 2, H - 120), "ナレーション: VOICEVOX:四国めたん", font=font(34), fill=(60, 40, 60, 210), anchor="mm")
    d.text((W / 2, H - 70), "BGM: オリジナル(合成)", font=font(30), fill=(60, 40, 60, 170), anchor="mm")

    L = {}
    dd = ImageDraw.Draw(bg)
    if kind == "item":
        L["num"] = text_layer([str(idx)], font(520), (255, 255, 255, 255), stroke=14, stroke_fill=accent + (255,),
                              shadow=(0, 0, 0, 60))
        f = font(96)
        L["head"] = text_layer(wrap(dd, head, f, 900), f, (40, 30, 50, 255), stroke=3, stroke_fill=(40, 30, 50, 255))
        fs = font(58)
        sub_im = text_layer(wrap(dd, sub, fs, 880), fs, (255, 255, 255, 255), stroke=2, stroke_fill=accent + (255,))
        # 角丸の帯
        pad = Image.new("RGBA", (sub_im.width + 40, sub_im.height - 20), (0, 0, 0, 0))
        ImageDraw.Draw(pad).rounded_rectangle((0, 0, pad.width - 1, pad.height - 1), 50, fill=accent + (235,))
        pad.alpha_composite(sub_im, (20, -30))
        L["sub"] = pad
    else:
        fa = font(120 if kind == "intro" else 130)
        L["head"] = text_layer([head], font(110), (40, 30, 50, 255), stroke=3, stroke_fill=(40, 30, 50, 255))
        L["sub"] = text_layer(wrap(dd, sub, fa, 900), fa, (255, 255, 255, 255), stroke=12, stroke_fill=accent + (255,),
                              shadow=(0, 0, 0, 55))
        if kind == "intro":
            L["badge"] = text_layer(["TOP 10"], font(150), accent + (255,), stroke=0)
    return bg, L


def render_frame(bg, L, kind, t):
    fr = bg.copy()
    a1 = min(1, t / 0.35)
    a2 = min(1, max(0, (t - 0.12) / 0.35))
    a3 = min(1, max(0, (t - 0.28) / 0.35))
    if kind == "item":
        paste_center(fr, L["num"], W / 2, 620, scale=ease_out_back(a1) * 1.0, alpha=min(1, a1 * 2))
        paste_center(fr, L["head"], W / 2, 1180, alpha=ease_out(a2), dy=(1 - ease_out(a2)) * 70)
        paste_center(fr, L["sub"], W / 2, 1460, alpha=ease_out(a3), dy=(1 - ease_out(a3)) * 70)
    elif kind == "intro":
        paste_center(fr, L["badge"], W / 2, 560, scale=ease_out_back(a1), alpha=min(1, a1 * 2))
        paste_center(fr, L["head"], W / 2, 900, alpha=ease_out(a2), dy=(1 - ease_out(a2)) * 70)
        paste_center(fr, L["sub"], W / 2, 1100, alpha=ease_out(a3), scale=0.9 + 0.1 * ease_out_back(a3))
    else:
        paste_center(fr, L["head"], W / 2, 800, alpha=ease_out(a1), dy=(1 - ease_out(a1)) * 70)
        paste_center(fr, L["sub"], W / 2, 1020, alpha=ease_out(a2), scale=0.9 + 0.1 * ease_out_back(a2))
    return fr.convert("RGB")


# ---------------------------------------------------------------- BGM
SR = 44100


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def synth_bgm(total, bpm=128):
    n = int(total * SR) + SR
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    prog = [  # C - G - Am - F
        ([48, 52, 55], 60), ([43, 47, 50], 59), ([45, 48, 52], 57), ([41, 45, 48], 60),
    ]

    def add(sig, start):
        i = int(start * SR)
        if i >= n:
            return
        e = min(n, i + len(sig))
        out[i:e] += sig[: e - i]

    def pluck(freq, dur, vol):
        t = np.arange(int(dur * SR)) / SR
        s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.15 * np.sin(6 * np.pi * freq * t))
        env = np.exp(-t * 7.0) * np.minimum(1, t / 0.004)
        return (s * env * vol).astype(np.float32)

    def pad(freqs, dur, vol):
        t = np.arange(int(dur * SR)) / SR
        s = sum(np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.004 * t) for f in freqs)
        env = np.minimum(1, t / 0.25) * np.minimum(1, (dur - t) / 0.3)
        return (s * env * vol / len(freqs)).astype(np.float32)

    def kick(vol):
        t = np.arange(int(0.22 * SR)) / SR
        f = 120 * np.exp(-t * 22) + 42
        ph = 2 * np.pi * np.cumsum(f) / SR
        return (np.sin(ph) * np.exp(-t * 14) * vol).astype(np.float32)

    rng = np.random.default_rng(7)

    def hat(vol):
        t = np.arange(int(0.05 * SR)) / SR
        return (rng.standard_normal(len(t)) * np.exp(-t * 90) * vol).astype(np.float32)

    bar = beat * 4
    nbars = int(total / bar) + 2
    for b in range(nbars):
        chord, top = prog[b % 4]
        t0 = b * bar
        add(pad([midi(x + 12) for x in chord], bar, 0.20), t0)
        # ベース
        for k in range(4):
            add(pluck(midi(chord[0]), beat * 0.9, 0.30), t0 + k * beat)
        # アルペジオ(8分)
        notes = [chord[0] + 24, chord[1] + 24, chord[2] + 24, chord[1] + 36]
        seq = [0, 1, 2, 3, 2, 1, 2, 3]
        for k in range(8):
            add(pluck(midi(notes[seq[k]]), beat * 0.6, 0.16), t0 + k * beat / 2)
        # ドラム
        for k in range(4):
            add(kick(0.55), t0 + k * beat)
            add(hat(0.10), t0 + k * beat + beat / 2)
    out = out[: int(total * SR)]
    # フェード
    fi, fo = int(0.8 * SR), int(2.0 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    out /= max(1e-6, np.abs(out).max())
    return (out * 0.9)


def write_wav(path, sig, sr=SR):
    pcm = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- main
def main():
    scenes = [("intro", 0, *INTRO)] + [("item", 10 - i, *it) for i, it in enumerate(ITEMS)] + [("outro", 11, *OUTRO)]

    # 1) ナレーション生成
    print("== narration ==")
    voice = []
    for si, (kind, idx, head, sub, text) in enumerate(scenes):
        p = os.path.join(WORK, f"v{si:02d}.wav")
        tts(text, p)
        voice.append((p, wav_len(p)))
        print(si, f"{voice[-1][1]:.2f}s", text)

    # 2) タイミング
    LEAD, TAIL = 0.1, 0.15
    starts, t = [], 0.0
    durs = []
    for _, d in voice:
        starts.append(t)
        sd = LEAD + d + TAIL
        durs.append(sd)
        t += sd
    total = t + 0.4
    print(f"total {total:.1f}s")

    # 3) 音声ミックス (ナレーション + BGM)
    sr_v = 24000
    narr = np.zeros(int(total * SR) + SR, np.float32)
    for (p, d), s in zip(voice, starts):
        with wave.open(p) as w:
            sr = w.getframerate()
            ch = w.getnchannels()
            raw = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if ch > 1:
            raw = raw.reshape(-1, ch).mean(1)
        # リサンプル(線形)
        n_out = int(len(raw) * SR / sr)
        raw = np.interp(np.linspace(0, len(raw) - 1, n_out), np.arange(len(raw)), raw).astype(np.float32)
        i = int((s + LEAD) * SR)
        narr[i:i + len(raw)] += raw
    narr = narr[: int(total * SR)]
    narr /= max(1e-6, np.abs(narr).max())
    bgm = synth_bgm(total)
    # 簡易ダッキング: ナレーション包絡でBGMを下げる
    env = np.abs(narr)
    k = int(0.15 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = 1.0 - 0.55 * np.clip(env * 6, 0, 1)
    mix = narr * 0.95 + bgm * 0.32 * duck
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    audio_path = os.path.join(WORK, "mix.wav")
    write_wav(audio_path, mix)
    write_wav(os.path.join(OUT, "bgm_only.wav"), bgm * 0.8)

    # 4) 映像描画 → ffmpeg
    print("== video ==")
    silent = os.path.join(WORK, "silent.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
         silent], stdin=subprocess.PIPE)
    total_frames = int(round(total * FPS))
    fno = 0
    for si, (kind, idx, head, sub, text) in enumerate(scenes):
        pal = PALETTES[(idx - 1) % 10] if kind == "item" else (PALETTES[0] if kind == "intro" else PALETTES[9])
        if kind == "intro":
            pal = ((255, 214, 102), (255, 126, 121), (200, 50, 80))
        if kind == "outro":
            pal = ((137, 247, 254), (255, 154, 158), (214, 51, 108))
        bg, L = build_scene(idx, kind, head, sub, pal[2], pal[:2])
        sc_frames = int(round(durs[si] * FPS)) if si < len(scenes) - 1 else total_frames - fno
        static = None
        for f in range(sc_frames):
            t = f / FPS
            if t < 1.0:
                ff.stdin.write(render_frame(bg, L, kind, t).tobytes())
            else:
                if static is None:
                    static = render_frame(bg, L, kind, 1.0).tobytes()
                ff.stdin.write(static)
            fno += 1
        print("scene", si, "frames", sc_frames)
    ff.stdin.close()
    ff.wait()

    final = os.path.join(OUT, "koukou_sotsugyo_top10.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", audio_path, "-c:v", "copy",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])
    print("done:", final)


if __name__ == "__main__":
    main()
