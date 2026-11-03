# -*- coding: utf-8 -*-
"""スライド画像・ナレーション・BGM・字幕を ffmpeg で 1 本の MP4 にまとめる。
使い方: python3 build_video.py <slides_dir> <voice_dir> <work_dir> <out.mp4>
"""
import sys, os, json, subprocess
from scenario import SCENES

SLIDES, VOICE, WORK, OUT = sys.argv[1:5]
os.makedirs(WORK, exist_ok=True)
FPS = 30; W, H = 1920, 1080
PRE, POST = 0.35, 0.55   # ナレーション前後の余白（秒）
XF = 0.5                 # クロスフェード長（秒）
BGM_VOL = 0.19
VOICE_GAIN = 2.3   # ナレーションを約 +5dB（YouTube 向けに十分な音量へ）

timings = json.load(open(os.path.join(VOICE, "timings.json")))
durs = [round(PRE + t["duration"] + POST, 3) for t in timings]
starts = []  # 各シーンの開始時刻（クロスフェード重なりを考慮）
t = 0.0
for i, d in enumerate(durs):
    starts.append(round(t, 3)); t += d - XF
total = round(t + XF, 3)
print("scenes", len(durs), "total", total, "sec")

# ---- BGM ----
bgm = os.path.join(WORK, "bgm.wav")
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "make_bgm.py"), str(total + 0.5), bgm], check=True)

# ---- 字幕 (ASS) ----
def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"
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
            f.write(f"Dialogue: 0,{ts(base + c['start'])},{ts(base + c['end'] + 0.15)},Default,,0,0,0,,{c['text']}\n")

# ---- ffmpeg ----
cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
slide_files = sorted(f for f in os.listdir(SLIDES) if f.endswith(".png"))
assert len(slide_files) == len(timings) == len(SCENES)
for sf in slide_files:
    cmd += ["-i", os.path.join(SLIDES, sf)]
for tm in timings:
    cmd += ["-i", tm["file"]]
cmd += ["-i", bgm]
n = len(timings); bgm_idx = 2 * n
fc = []
# 映像：ゆっくりズーム（4K に拡大してから zoompan でジッター回避）
for i, d in enumerate(durs):
    frames = int(round(d * FPS))
    zoom_in = (i % 2 == 0)
    z = f"1+0.06*on/{frames}" if zoom_in else f"1.06-0.06*on/{frames}"
    fc.append(f"[{i}:v]scale={W*2}:{H*2}:flags=lanczos,zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
# クロスフェード連結
prev = "v0"
for i in range(1, n):
    off = round(starts[i], 3)
    out = f"x{i}" if i < n - 1 else "xv"
    fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={off}[{out}]")
    prev = out
fc.append(f"[xv]fade=t=in:st=0:d=0.6,fade=t=out:st={total-1.0:.3f}:d=1.0,ass={ass}[vout]")
# 音声：ナレーションを各シーン開始位置に配置して BGM とミックス
voices = []
for i in range(n):
    ms = int((starts[i] + PRE) * 1000)
    fc.append(f"[{n+i}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    voices.append(f"[a{i}]")
fc.append("".join(voices) + f"amix=inputs={n}:normalize=0:duration=longest,volume={VOICE_GAIN}[narr]")
fc.append(f"[{bgm_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={BGM_VOL},atrim=0:{total},afade=t=out:st={total-2.5:.3f}:d=2.5[bgm]")
fc.append("[narr][bgm]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[aout]")
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", OUT]
open(os.path.join(WORK, "ffmpeg_cmd.txt"), "w").write(" ".join(cmd))
subprocess.run(cmd, check=True)
print("done", OUT)
