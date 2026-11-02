# -*- coding: utf-8 -*-
"""Build pipeline: HTML per step -> PNG (Playwright) -> TTS audio -> ffmpeg assembly."""
import json, os, subprocess, sys, wave, html
import numpy as np
from script import SLIDES
import illustrations as I

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/build"
os.makedirs(OUT, exist_ok=True)
FPS = 30
LEAD, TAIL = 0.45, 0.75      # silence around each narration (sec)
XFADE = 0.6                  # crossfade between slides (sec)
TOTAL_SLIDES = len(SLIDES)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden;background:#f6f3e7;font-family:'IPAPGothic','IPAGothic',sans-serif;color:#2b3a2f}
.header{height:120px;background:#3d7a4a;display:flex;align-items:center;padding:0 60px;gap:28px;position:relative}
.tag{background:#f6c344;color:#2b3a2f;font-weight:bold;font-size:30px;padding:10px 26px;border-radius:40px;white-space:nowrap}
.title{color:#fff;font-size:52px;font-weight:bold;letter-spacing:1px}
.progress{position:absolute;left:0;bottom:0;height:8px;background:#f6c344}
.main{display:flex;height:780px}
.text{width:1120px;padding:60px 40px 0 70px;display:flex;flex-direction:column;gap:30px}
.illus{width:800px;display:flex;align-items:center;justify-content:center;padding:20px}
.illus svg{width:760px;height:700px;border-radius:24px;box-shadow:0 12px 30px rgba(0,0,0,.10)}
.bullet{display:flex;gap:22px;align-items:flex-start;font-size:38px;line-height:1.45;padding:18px 26px;border-radius:18px;background:#fff;border-left:14px solid #cfd8c8;visibility:hidden}
.bullet.shown{visibility:visible}
.bullet.current{border-left-color:#e0734a;background:#fff7f1;box-shadow:0 8px 20px rgba(224,115,74,.18)}
.bullet .num{flex:none;width:52px;height:52px;border-radius:50%;background:#3d7a4a;color:#fff;font-size:28px;font-weight:bold;display:flex;align-items:center;justify-content:center;margin-top:4px}
.bullet.current .num{background:#e0734a}
.note{font-size:24px;color:#6a7a6a;margin-top:auto;padding-bottom:16px}
.caption{height:180px;background:#2b3a2f;color:#fff;display:flex;align-items:center;justify-content:center;padding:0 90px;font-size:33px;line-height:1.5;text-align:center}
.caption span{display:block}
/* title slide */
body.title-slide .main{height:780px;flex-direction:row}
.bigtitle{width:1120px;display:flex;flex-direction:column;justify-content:center;padding:0 60px 0 90px;gap:36px}
.bigtitle h1{font-size:96px;line-height:1.25;color:#2b3a2f}
.bigtitle h1 b{color:#3d7a4a}
.bigtitle p{font-size:40px;color:#5a6a5a;line-height:1.5}
.pills{display:flex;gap:20px;margin-top:10px}
.pill{font-size:30px;font-weight:bold;padding:12px 30px;border-radius:40px;color:#fff}
"""

def page(slide, idx, step_i, narration):
    scene_svg = I.SCENES[slide["scene"]]()
    cap = f'<div class="caption"><span>{html.escape(narration)}</span></div>'
    prog = f'<div class="progress" style="width:{(idx+1)/TOTAL_SLIDES*1920:.0f}px"></div>'
    if slide.get("kind") == "title":
        body = f"""
<body class="title-slide">
<div class="header"><div class="title">農業への転職ガイド</div>{prog}</div>
<div class="main">
 <div class="bigtitle"><h1>脱サラして<br><b>農家になる方法</b><br>３選</h1>
  <p>自分に合ったルートを、基礎知識から丁寧に解説します</p>
  <div class="pills"><span class="pill" style="background:#4c8a3f">① 新規就農</span><span class="pill" style="background:#2f8f8f">② 雇用就農</span><span class="pill" style="background:#e0734a">③ 継承</span></div>
 </div>
 <div class="illus">{scene_svg}</div>
</div>{cap}</body>"""
    else:
        bullets = ""
        for j, (b, _) in enumerate(slide["steps"]):
            cls = "bullet" + (" shown" if j <= step_i else "") + (" current" if j == step_i else "")
            bullets += f'<div class="{cls}"><div class="num">{j+1}</div><div>{html.escape(b)}</div></div>'
        note = f'<div class="note">{html.escape(slide["note"])}</div>' if slide.get("note") else ""
        body = f"""
<body>
<div class="header"><div class="tag">{html.escape(slide["tag"])}</div><div class="title">{html.escape(slide["title"])}</div>{prog}</div>
<div class="main"><div class="text">{bullets}{note}</div><div class="illus">{scene_svg}</div></div>{cap}</body>"""
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>{CSS}</style></head>{body}</html>'

# ---------- 1. HTML ----------
steps = []
for si, slide in enumerate(SLIDES):
    for ti, (b, narr) in enumerate(slide["steps"]):
        name = f"s{si:02d}_{ti:02d}"
        with open(f"{OUT}/{name}.html", "w", encoding="utf-8") as f:
            f.write(page(slide, si, ti, narr))
        steps.append(dict(name=name, slide=si, narr=narr))
json.dump(steps, open(f"{OUT}/steps.json", "w"), ensure_ascii=False, indent=1)
print("html:", len(steps), "steps")

# ---------- 2. Screenshots ----------
subprocess.run(["node", os.path.join(os.path.dirname(__file__), "render.js"), OUT], check=True)

# ---------- 3. TTS ----------
import pyopenjtalk
SR = 48000
READINGS = {"作目": "さくもく", "お米": "おこめ"}   # words Open JTalk misreads
def tts(text):
    for k, v in READINGS.items():
        text = text.replace(k, v)
    x, sr = pyopenjtalk.tts(text, speed=1.0, half_tone=0.0)
    assert sr == SR
    x = x.astype(np.float32) / 32768.0
    return x

def write_wav(path, x):
    with wave.open(path, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

slide_audio = {}
peak = 0
for st in steps:
    a = tts(st["narr"])
    peak = max(peak, float(np.abs(a).max()))
    st["_a"] = a
for st in steps:
    a = st["_a"] / peak * 0.85
    a = np.concatenate([np.zeros(int(LEAD * SR), np.float32), a, np.zeros(int(TAIL * SR), np.float32)])
    st["dur"] = len(a) / SR
    slide_audio.setdefault(st["slide"], []).append(a)
    del st["_a"]
    print(f"  {st['name']} {st['dur']:.2f}s")

# ---------- 4. Per-slide video ----------
slide_files = []
for si in range(TOTAL_SLIDES):
    parts = [s for s in steps if s["slide"] == si]
    audio = np.concatenate(slide_audio[si])
    write_wav(f"{OUT}/a{si:02d}.wav", audio)
    total = len(audio) / SR
    with open(f"{OUT}/c{si:02d}.txt", "w") as f:
        for s in parts:
            f.write(f"file '{OUT}/{s['name']}.png'\nduration {s['dur']:.3f}\n")
        f.write(f"file '{OUT}/{parts[-1]['name']}.png'\n")
    outv = f"{OUT}/v{si:02d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{OUT}/c{si:02d}.txt",
                    "-i", f"{OUT}/a{si:02d}.wav", "-t", f"{total:.3f}",
                    "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "pcm_s16le", outv], check=True)
    slide_files.append((outv, total))
    print(f"slide {si} {total:.2f}s")

# ---------- 5. Crossfade slides together ----------
n = len(slide_files)
inputs = []
for f_, _ in slide_files:
    inputs += ["-i", f_]
fc = []
off = 0.0
for i in range(1, n):
    off += slide_files[i - 1][1] - XFADE
    vin = "[0:v]" if i == 1 else f"[v{i-1}]"
    ain = "[0:a]" if i == 1 else f"[a{i-1}]"
    fc.append(f"{vin}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={off:.3f}[v{i}]")
    fc.append(f"{ain}[{i}:a]acrossfade=d={XFADE}:c1=tri:c2=tri[a{i}]")
total_len = sum(d for _, d in slide_files) - XFADE * (n - 1)

# ---------- 6. Soft background music ----------
def bgm(length):
    t = np.arange(int(length * SR)) / SR
    out = np.zeros_like(t, dtype=np.float32)
    chords = [[261.63, 329.63, 392.00, 523.25], [196.00, 246.94, 293.66, 392.00],
              [220.00, 261.63, 329.63, 440.00], [174.61, 220.00, 261.63, 349.23]]
    bar = 4.0
    nb = int(np.ceil(length / bar))
    for b in range(nb):
        ch = chords[b % 4]
        s0, s1 = int(b * bar * SR), min(int((b + 1) * bar * SR), len(t))
        if s0 >= len(t): break
        tt = t[s0:s1] - b * bar
        env = np.minimum(tt / 0.8, 1.0) * np.minimum((bar - tt) / 0.8, 1.0)
        env = np.clip(env, 0, 1)
        seg = np.zeros_like(tt)
        for f in ch:
            seg += np.sin(2 * np.pi * f / 2 * tt) * 0.5 + np.sin(2 * np.pi * f * tt) * 0.35 + np.sin(2 * np.pi * f * 2 * tt) * 0.08
        # gentle arpeggio
        for k in range(8):
            a0 = k * bar / 8
            m = (tt >= a0)
            tk = tt[m] - a0
            f = ch[k % 4] * 2
            seg[m] += np.sin(2 * np.pi * f * tk) * np.exp(-tk * 3.5) * 0.25
        out[s0:s1] += (seg * env).astype(np.float32)
    out /= np.abs(out).max()
    fade = int(min(5.0, length / 4) * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[:int(2 * SR)] *= np.linspace(0, 1, int(2 * SR))
    return out * 0.07
write_wav(f"{OUT}/bgm.wav", bgm(total_len + 1))

final = f"{OUT}/final_nobgm.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc),
                "-map", f"[v{n-1}]", "-map", f"[a{n-1}]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", final], check=True)
dest = sys.argv[2] if len(sys.argv) > 2 else f"{OUT}/final.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", final, "-i", f"{OUT}/bgm.wav",
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dest], check=True)
print("DONE", dest, f"{total_len/60:.1f} min")
