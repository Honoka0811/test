# -*- coding: utf-8 -*-
"""スライド画像・ナレーション・BGM・効果音・字幕を ffmpeg で 1 本の MP4 にまとめる。
- 箇条書きはナレーションの文の進行に合わせて 1 つずつ表示（段階画像を切り替え）
- シーン間はクロスフェード、各シーンにゆっくりズーム
- 画面下に再生位置の進捗バー
- 箇条書き表示時の「ポップ音」、シーン切り替えの「スウッシュ音」を合成してミックス
- YouTube 概要欄用のチャプター一覧 (chapters.txt) を出力
使い方: python3 build_video.py <slides_dir> <voice_dir> <work_dir> <out.mp4>
"""
import sys, os, json, math, subprocess, wave
import numpy as np
from scenario import SCENES

SLIDES, VOICE, WORK, OUT = sys.argv[1:5]
os.makedirs(WORK, exist_ok=True)
FPS = 30; W, H = 1920, 1080
PRE, POST = 0.35, 0.55   # ナレーション前後の余白（秒）
XF = 0.5                 # クロスフェード長（秒）
BGM_VOL = 0.19
VOICE_GAIN = 2.3
SFX_VOL = 0.35
SR = 48000

timings = json.load(open(os.path.join(VOICE, "timings.json")))
assert len(timings) == len(SCENES)
durs = [round(max(PRE + t["duration"] + POST, 3.2 if sc["kind"] == "part" else 0), 3) for t, sc in zip(timings, SCENES)]  # 区切りカードは最低 3.2 秒
starts = []; t = 0.0
for d in durs:
    starts.append(round(t, 3)); t += d - XF
total = round(t + XF, 3)
print("scenes", len(durs), "total", total, "sec")

# ---- 段階（stage）の計算：文 j が終わった時点で表示する箇条書き数 = ceil((j+1)*nb/ns) ----
def stages_for(i):
    sc = SCENES[i]; tm = timings[i]; nb = len(sc["bullets"]); ns = len(tm["cues"])
    if sc["kind"] == "part" or nb == 0:
        return [(0, durs[i])]
    # 各文の開始時刻（シーン内、PRE を含む）で表示数が変わる
    marks = []  # (time, visible)
    for j, c in enumerate(tm["cues"]):
        vis = min(nb, math.ceil((j + 1) * nb / ns))
        marks.append((PRE + c["start"], vis))
    # 先頭は文0の表示数を 0 秒から（最初の文が始まる前は 0 でもよいが、空白を避けるため文0の数を使う）
    out = []; cur_vis = marks[0][1]; cur_t = 0.0
    for tt, vis in marks[1:]:
        if vis != cur_vis:
            out.append((cur_vis, round(tt - cur_t, 3))); cur_t = tt; cur_vis = vis
    out.append((cur_vis, round(durs[i] - cur_t, 3)))
    return out

stage_plan = [stages_for(i) for i in range(len(SCENES))]

# ---- 効果音（numpy 合成）を 1 本のトラックにまとめる ----
def pop(n=int(0.12 * SR)):
    tt = np.arange(n) / SR
    f = 900 * np.exp(-tt * 25) + 420
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 28) * 0.8
def whoosh(n=int(0.45 * SR)):
    rng = np.random.default_rng(1); x = rng.standard_normal(n)
    tt = np.arange(n) / SR
    env = np.sin(np.pi * tt / (n / SR)) ** 2
    k = 401; win = np.hanning(k); win /= win.sum()
    low = np.convolve(x, win, mode="same")
    return (x - low) * env * 0.35
sfx = np.zeros(int((total + 1) * SR))
def place(snd, at):
    s0 = int(at * SR); e = min(len(sfx), s0 + len(snd))
    if s0 < len(sfx): sfx[s0:e] += snd[: e - s0]
events = []
for i, st in enumerate(stage_plan):
    tt = starts[i]
    for k, (vis, d) in enumerate(st):
        if k > 0: place(pop(), tt); events.append(("pop", round(tt, 2)))
        tt += d
    if i > 0: place(whoosh(), starts[i] - 0.15); events.append(("whoosh", round(starts[i], 2)))
sfx = np.clip(sfx * SFX_VOL, -1, 1)
sfx_path = os.path.join(WORK, "sfx.wav")
with wave.open(sfx_path, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.stack([sfx, sfx], 1) * 32767).astype(np.int16).tobytes())
print("sfx events", len(events))

# ---- BGM ----
bgm = os.path.join(WORK, "bgm.wav")
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_bgm.py"), str(total + 0.5), bgm], check=True)

# ---- 字幕 (ASS) ----
def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"
def wrap(text, limit=30):
    if len(text) <= limit: return text
    mid = len(text) // 2
    cands = [k for k, ch in enumerate(text) if ch in "、，" and 8 <= k <= len(text) - 8]
    cut = (min(cands, key=lambda k: abs(k - mid)) + 1) if cands else mid
    return text[:cut] + "\\N" + text[cut:]
ass = os.path.join(WORK, "subs.ass")
with open(ass, "w", encoding="utf-8") as f:
    f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK JP,52,&H00FFFFFF,&H00FFFFFF,&H00261A12,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,0,2,160,160,56,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    for i, tm in enumerate(timings):
        base = starts[i] + PRE
        for c in tm["cues"]:
            f.write(f"Dialogue: 0,{ts(base + c['start'])},{ts(base + c['end'] + 0.15)},Default,,0,0,0,,{wrap(c['text'])}\n")

# ---- チャプター（YouTube 概要欄用） ----
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chapters.txt"), "w", encoding="utf-8") as f:
    for i, sc in enumerate(SCENES):
        if sc.get("chapter"):
            m, s = divmod(int(starts[i]), 60); f.write(f"{m}:{s:02d} {sc['chapter']}\n")

# ---- ffmpeg ----
cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
inputs = []  # (scene, stage) ごとの画像
for i, sc in enumerate(SCENES):
    for k, (vis, d) in enumerate(stage_plan[i]):
        path = os.path.join(SLIDES, f"{i:02d}_{sc['id']}_s{vis}.png")
        assert os.path.exists(path), path
        cmd += ["-i", path]; inputs.append((i, k, d))
n_img = len(inputs)
for tm in timings: cmd += ["-i", tm["file"]]
cmd += ["-i", bgm, "-i", sfx_path]
n = len(timings); bgm_idx = n_img + n; sfx_idx = bgm_idx + 1
fc = []
# 映像：段階画像ごとにズーム（シーン内で連続するように開始ズームをずらす）
for i, sc in enumerate(SCENES):
    frames_total = int(round(durs[i] * FPS)); f0 = 0; labels = []
    zoom_in = (i % 2 == 0)
    for k, (vis, d) in enumerate(stage_plan[i]):
        idx = inputs.index((i, k, d)); fr = int(round(d * FPS))
        if k == len(stage_plan[i]) - 1: fr = frames_total - f0  # 丸め誤差を最後の段階で吸収
        z = f"1+0.06*(on+{f0})/{frames_total}" if zoom_in else f"1.06-0.06*(on+{f0})/{frames_total}"
        fc.append(f"[{idx}:v]scale={W*2}:{H*2}:flags=lanczos,zoompan=z='{z}':d={fr}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[p{i}_{k}]")
        labels.append(f"[p{i}_{k}]"); f0 += fr
    # concat 後は timebase が変わるため、xfade のために 1/FPS に揃える
    if len(labels) == 1: fc.append(f"{labels[0]}settb=1/{FPS}[v{i}]")
    else: fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0,fps={FPS},settb=1/{FPS}[v{i}]")
prev = "v0"
for i in range(1, n):
    out = f"x{i}" if i < n - 1 else "xv"
    fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={starts[i]}[{out}]")
    prev = out
# 進捗バー（画面下、赤）＋フェード＋字幕
fc.append(f"[xv]drawbox=x=0:y={H-8}:w='iw*t/{total}':h=8:color=0xD6203A@0.95:thickness=fill,"
          f"fade=t=in:st=0:d=0.6,fade=t=out:st={total-1.0:.3f}:d=1.0,ass={ass}[vout]")
# 音声
voices = []
for i in range(n):
    ms = int((starts[i] + PRE) * 1000)
    fc.append(f"[{n_img+i}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    voices.append(f"[a{i}]")
fc.append("".join(voices) + f"amix=inputs={n}:normalize=0:duration=longest,volume={VOICE_GAIN}[narr]")
fc.append(f"[{bgm_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={BGM_VOL},atrim=0:{total},afade=t=out:st={total-2.5:.3f}:d=2.5[bgm]")
fc.append(f"[{sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,atrim=0:{total}[sfx]")
fc.append("[narr][bgm][sfx]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[aout]")
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", OUT]
open(os.path.join(WORK, "ffmpeg_cmd.txt"), "w").write(" ".join(cmd))
subprocess.run(cmd, check=True)
print("done", OUT)
