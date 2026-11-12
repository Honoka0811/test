import json, math, os, subprocess, urllib.parse, urllib.request, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SPEAKER = 2  # 四国めたん ノーマル
SR = 24000

FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# (ナレーション, テロップ見出し, 絵文字アイコン)
SCENES = [
    ("夢のお仕事？ウォータースライダーのテスターって知ってる？", "ウォータースライダー\nテスター", "🌊"),
    ("新しいスライダーを実際に滑って、安全性と楽しさをチェックするお仕事なの。", "安全性と楽しさを\nチェック！", "✅"),
    ("まずは砂袋やダミー人形を流して、速度やジーをセンサーで測定するわ。", "STEP1\nダミーで計測", "📏"),
    ("数値がオーケーなら、いよいよ人間の出番。体重や体格の違う人で、何度も滑るのよ。", "STEP2\n人が実際に滑る", "🏊"),
    ("スピードは速すぎないか、体が浮く場所はないか、着水は安全か。しっかり確認するの。", "チェック項目", "🔍"),
    ("イギリスの旅行会社が、世界中のスライダーを滑るテスターを募集して、話題になったこともあるわ。", "世界のリゾートを\n滑る求人も！", "🌴"),
    ("ただし、専任のお仕事はとってもレア。何百回も滑るから、体力勝負なのよ。", "実はレア＆\n体力勝負", "💪"),
    ("あなたも挑戦してみたい？フォローしてね！", "あなたも\n挑戦したい？", "🙌"),
]
SUBS = {  # 字幕表示用（読み替えを戻す）
    2: "まずは砂袋やダミー人形を流して、速度やGをセンサーで測定するわ。",
    3: "数値がOKなら、いよいよ人間の出番。体重や体格の違う人で、何度も滑るのよ。",
}
CHECKS = ["スピードは速すぎない？", "体が浮く場所はない？", "着水は安全？"]


def tts(text, path):
    q = urllib.parse.quote(text)
    req = urllib.request.Request(f"http://localhost:50021/audio_query?text={q}&speaker={SPEAKER}", method="POST")
    query = json.loads(urllib.request.urlopen(req).read())
    query["speedScale"] = 1.15
    query["intonationScale"] = 1.2
    query["prePhonemeLength"] = 0.05
    query["postPhonemeLength"] = 0.1
    req = urllib.request.Request(f"http://localhost:50021/synthesis?speaker={SPEAKER}",
                                 data=json.dumps(query).encode(), headers={"Content-Type": "application/json"})
    open(path, "wb").write(urllib.request.urlopen(req).read())


def read_wav(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


# ---------- ナレーション ----------
GAP = 0.35
voice_parts, timeline, t = [], [], 0.4
voice_parts.append(np.zeros(int(SR * 0.4), np.float32))
for i, (text, _, _) in enumerate(SCENES):
    p = os.path.join(OUT, f"v{i}.wav")
    tts(text, p)
    a = read_wav(p)
    dur = len(a) / SR
    timeline.append((t, t + dur))
    voice_parts += [a, np.zeros(int(SR * GAP), np.float32)]
    t += dur + GAP
total = t + 1.0
voice = np.concatenate(voice_parts)
voice = np.pad(voice, (0, int(total * SR) - len(voice)))

# ---------- BGM（自作の軽快なトロピカル風）----------
BPM = 124
beat = 60 / BPM
n = len(voice)
tt = np.arange(n) / SR
bgm = np.zeros(n, np.float32)
# C - G - Am - F
chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
bass = [36, 43, 45, 41]
mfreq = lambda m: 440 * 2 ** ((m - 69) / 12)


def add(start, dur, freq, amp, kind="pluck"):
    s = int(start * SR)
    if s >= n:
        return
    L = min(int(dur * SR), n - s)
    x = np.arange(L) / SR
    if kind == "pluck":  # マリンバ風
        env = np.exp(-x * 9)
        sig = np.sin(2 * np.pi * freq * x) + 0.3 * np.sin(2 * np.pi * freq * 4 * x) * np.exp(-x * 30)
    elif kind == "bass":
        env = np.exp(-x * 4) * np.minimum(1, x * 200)
        sig = np.sin(2 * np.pi * freq * x) + 0.2 * np.sin(2 * np.pi * freq * 2 * x)
    elif kind == "kick":
        env = np.exp(-x * 18)
        sig = np.sin(2 * np.pi * (50 + 90 * np.exp(-x * 30)) * x)
    elif kind == "hat":
        env = np.exp(-x * 60)
        sig = np.random.uniform(-1, 1, L)
        sig = np.diff(sig, prepend=0)
    bgm[s:s + L] += (amp * env * sig).astype(np.float32)


arp_pattern = [0, 1, 2, 1, 2, 0, 1, 2]
nbars = int(total / (beat * 4)) + 1
for bar in range(nbars):
    ch = chords[bar % 4]
    b0 = bar * beat * 4
    for k in range(8):
        note = ch[arp_pattern[k]] + 12
        add(b0 + k * beat / 2, 0.5, mfreq(note), 0.18)
    for k in range(4):
        add(b0 + k * beat, 0.35, 0, 0.5, "kick")
        add(b0 + k * beat + beat / 2, 0.08, 0, 0.06, "hat")
    add(b0, beat * 1.5, mfreq(bass[bar % 4]), 0.35, "bass")
    add(b0 + beat * 2.5, beat * 1.5, mfreq(bass[bar % 4]), 0.3, "bass")
# フェードイン/アウト
fade = np.ones(n, np.float32)
fi, fo = int(0.5 * SR), int(1.5 * SR)
fade[:fi] = np.linspace(0, 1, fi)
fade[-fo:] = np.linspace(1, 0, fo)
bgm *= fade
bgm = bgm / np.max(np.abs(bgm)) * 0.16

# ナレーション中はBGMを少し下げる（ダッキング）
env = np.convolve(np.abs(voice) > 0.02, np.ones(int(SR * 0.3)) / (SR * 0.3), mode="same")
duck = 1 - 0.45 * np.clip(env * 3, 0, 1)
mix = voice * 0.95 + bgm * duck
mix = np.clip(mix, -1, 1)
with wave.open(os.path.join(OUT, "mix.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

# ---------- 映像 ----------
f_title = ImageFont.truetype(FONT, 110)
f_sub = ImageFont.truetype(FONT, 58)
f_small = ImageFont.truetype(FONT, 36)
f_check = ImageFont.truetype(FONT, 64)
f_emoji = ImageFont.truetype(EMOJI, 109)


def emoji_img(ch, size):
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((80, 80), ch, font=f_emoji, embedded_color=True, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


EMOJI_CACHE = {s[2]: emoji_img(s[2], 220) for s in SCENES}
RIDER = emoji_img("🏄", 150)
SACK = emoji_img("🎒", 130)
CHECKMARK = emoji_img("✅", 80)

# 背景（空のグラデーション）
grad = np.zeros((H, W, 3), np.uint8)
for y in range(H):
    r = y / H
    grad[y] = (int(70 + 120 * r), int(180 + 50 * r), int(255 - 20 * r))
BG = Image.fromarray(grad)

# スライダーの経路（S字にくねるチューブ）
def path_pt(u):
    y = 820 + u * 820
    x = W / 2 + 330 * math.sin(u * math.pi * 2.6)
    return x, y

PATH = [path_pt(i / 300) for i in range(301)]


def wrap(text, font, maxw, draw):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > maxw and cur:
            if ch in "、。！？」ーャュョッァィゥェォ":
                cur += ch; lines.append(cur); cur = ""; continue
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def ease_out(x):
    x = max(0, min(1, x)); return 1 - (1 - x) ** 3


def frame(t):
    im = BG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    # 太陽
    d.ellipse((800, 120, 1000, 320), fill=(255, 236, 120, 255))
    # 雲
    for cx, cy, s in [(180, 260, 1.0), (620, 420, 0.7)]:
        cx = (cx + t * 25 * s) % (W + 300) - 150
        for dx, dy, r in [(0, 0, 60), (60, -25, 70), (130, 0, 55)]:
            d.ellipse((cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s), fill=(255, 255, 255, 230))
    # 支柱
    for u in [0.05, 0.3, 0.55, 0.8]:
        x, y = path_pt(u)
        d.rectangle((x - 10, y, x + 10, 1700), fill=(200, 200, 210, 255))
    # スライダー本体
    d.line(PATH, fill=(230, 80, 60, 255), width=110, joint="curve")
    d.line(PATH, fill=(255, 140, 90, 255), width=80, joint="curve")
    d.line(PATH, fill=(120, 210, 255, 200), width=40, joint="curve")
    # 流れる水しぶきの線
    for k in range(6):
        u = ((t * 0.35 + k / 6) % 1)
        i = int(u * 290)
        d.line(PATH[i:i + 10], fill=(255, 255, 255, 200), width=10)
    # プール
    d.rectangle((0, 1640, W, H), fill=(40, 150, 230, 255))
    for k in range(3):
        pts = [(x, 1650 + k * 60 + 14 * math.sin(x / 70 + t * 3 + k)) for x in range(0, W + 20, 20)]
        d.line(pts, fill=(255, 255, 255, 140), width=8)

    # 現在のシーン
    si = 0
    for i, (s, e) in enumerate(timeline):
        if t >= s - GAP * 0.5:
            si = i
    s0, e0 = timeline[si]
    local = t - (s0 - GAP * 0.5)

    # 滑る人（シーン2は砂袋）
    u = ((t - s0) / max(1.5, (e0 - s0))) % 1
    x, y = path_pt(u)
    sprite = SACK if si == 2 else RIDER
    im.alpha_composite(sprite, (int(x - sprite.width / 2), int(y - sprite.height / 2 - 30))) if im.mode == "RGBA" else None
    if im.mode != "RGBA":
        im = im.convert("RGBA"); d = ImageDraw.Draw(im, "RGBA")
        im.alpha_composite(sprite, (int(x - sprite.width / 2), int(y - sprite.height / 2 - 30)))

    # 速度メーター（ステップ1 / チェック項目）
    if si in (2,):
        spd = 30 + 15 * math.sin(t * 3) + 10
        d.rounded_rectangle((640, 1180, 1040, 1360), 30, fill=(20, 30, 60, 220))
        d.text((840, 1230), "SPEED", font=f_small, fill=(150, 220, 255), anchor="mm")
        d.text((840, 1305), f"{spd:4.1f} km/h", font=f_check, fill=(255, 255, 255), anchor="mm")

    # 見出しテロップ（ポップイン）
    _, title, emo = SCENES[si]
    sc = 0.6 + 0.4 * ease_out(local / 0.35) + 0.05 * math.sin(min(local, 0.6) / 0.6 * math.pi)
    layer = Image.new("RGBA", (W, 560), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((60, 40, W - 60, 520), 50, fill=(255, 255, 255, 235), outline=(30, 120, 220), width=10)
    fs = 110
    while True:
        ft = ImageFont.truetype(FONT, fs)
        if max(ld.textlength(l, font=ft) for l in title.split("\n")) <= W - 200: break
        fs -= 4
    ld.multiline_text((W / 2, 300), title, font=ft, fill=(20, 80, 180), anchor="mm", align="center",
                      spacing=20, stroke_width=3, stroke_fill=(20, 80, 180))
    layer = layer.resize((int(W * sc), int(560 * sc)), Image.LANCZOS)
    im.alpha_composite(layer, (int((W - layer.width) / 2), int(150 + 280 * (1 - sc))))
    e = EMOJI_CACHE[emo]
    bob = int(12 * math.sin(t * 4))
    im.alpha_composite(e, (W - 300, 40 + bob))

    # チェック項目リスト
    if si == 4:
        n_show = int(local / ((e0 - s0) / 3)) + 1
        for k, txt in enumerate(CHECKS[:min(3, n_show)]):
            yy = 770 + k * 130
            d.rounded_rectangle((90, yy, W - 90, yy + 110), 30, fill=(255, 255, 255, 240))
            im.alpha_composite(CHECKMARK, (120, yy + 15))
            d.text((230, yy + 55), txt, font=f_check, fill=(30, 30, 30), anchor="lm")

    # 字幕
    sub = SUBS.get(si, SCENES[si][0])
    lines = wrap(sub, f_sub, W - 160, d)
    lh = 76
    top = 1720 - (len(lines) * lh) / 2 - 40
    d.rounded_rectangle((50, top - 30, W - 50, top + len(lines) * lh + 20), 30, fill=(0, 0, 0, 160))
    for k, ln in enumerate(lines):
        d.text((W / 2, top + k * lh + 30), ln, font=f_sub, fill=(255, 255, 255), anchor="mm",
               stroke_width=4, stroke_fill=(230, 60, 140))
    # クレジット
    d.text((W - 30, H - 25), "VOICEVOX:四国めたん", font=f_small, fill=(255, 255, 255, 230), anchor="rb",
           stroke_width=2, stroke_fill=(0, 0, 0))
    return im.convert("RGB")


BG = BG.convert("RGBA")
nframes = int(total * FPS)
out = os.path.join(OUT, "waterslide_tester_short.mp4")
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "mix.wav"),
                       "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out],
                      stdin=subprocess.PIPE)
for f in range(nframes):
    ff.stdin.write(frame(f / FPS).tobytes())
ff.stdin.close(); ff.wait()
print("done", out, f"{total:.1f}s")
