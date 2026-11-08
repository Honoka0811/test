"""ショート動画をビルドする。

  python tts.py              # 先に VOICEVOX でナレーション生成（VOICEVOX 起動が必要）
  python build.py            # out/numbers_station_short.mp4 を出力
  python build.py --dry-run  # ナレーション無し（尺は文字数から推定）で映像と BGM を確認
"""
import argparse, os, subprocess, sys, wave
from multiprocessing import Pool

import numpy as np
from scipy.signal import resample_poly

import audio
import render
from scenes import SCENES, FREQ_LOCK_SCENE

OUT = "out"


def load_wav(path):
    with wave.open(path) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != audio.SR:
        g = np.gcd(sr, audio.SR)
        x = resample_poly(x, audio.SR // g, sr // g)
    return x


def estimate_secs(text):
    return 0.6 + len(text) * 0.135


def timeline(voices):
    scenes, t = [], 0.0
    lead = {"hook1": 0.35, "words": 0.25, "hidden": 0.7}
    for s, v in zip(SCENES, voices):
        d = dict(s)
        d["start"] = t
        d["vstart"] = t + lead.get(s["id"], 0.12)
        d["end"] = d["vstart"] + len(v) / audio.SR + 0.22
        t = d["end"]
        scenes.append(d)
    scenes[-1]["end"] += 1.4  # 余韻 → 砂嵐でループ
    lock = False
    for d in scenes:
        lock = lock or d["id"] == FREQ_LOCK_SCENE
        d["lock"] = lock
    return scenes, scenes[-1]["end"]


def events_for(scenes):
    ev = [(s["start"], "glitch") for s in scenes[1:]]
    for s in scenes:
        if s["visual"] == "radio_alert":
            ev.append((s["start"] + 0.3, "stamp"))
        if s["visual"] == "telegram":
            n = render.telegram_chars(0)
            ev += [(s["start"] + k / render.TYPE_CPS, "tick") for k in range(n)]
            ev.append((s["start"] + 1.6, "stamp"))
        if s["visual"] == "otp":
            ev += [(s["start"] + x, "tick") for x in render.otp_tick_times()]
            ev.append((s["start"] + 3.0, "stamp"))
    return ev


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(audio.SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def _init(scenes, total, mix):
    render.STATE.update(scenes=scenes, total=total, audio=mix, sr=audio.SR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seconds", type=float, default=None, help="先頭だけ書き出す（確認用）")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    voices = []
    for i, s in enumerate(SCENES):
        p = os.path.join(OUT, "voice", f"{i:02d}.wav")
        if os.path.exists(p) and not a.dry_run:
            voices.append(load_wav(p))
        elif a.dry_run:
            voices.append(np.zeros(int(estimate_secs(s["text"]) * audio.SR), np.float32))
        else:
            sys.exit(f"{p} がありません。先に python tts.py を実行するか --dry-run を付けてください。")

    scenes, total = timeline(voices)
    print(f"total {total:.2f}s")
    for s in scenes:
        print(f"  {s['start']:6.2f}-{s['end']:6.2f}  {s['id']}")
    mix, vo = audio.build_mix(total, scenes, voices, events_for(scenes))
    wav = os.path.join(OUT, "mix.wav")
    write_wav(wav, mix)

    dur = min(total, a.seconds or total)
    nframes = int(dur * render.FPS)
    out = a.out or os.path.join(OUT, "numbers_station_short_preview.mp4" if a.dry_run else "numbers_station_short.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{render.W}x{render.H}", "-r", str(render.FPS), "-i", "-",
           "-i", wav, "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=_init, initargs=(scenes, total, mix)) as pool:
        for k, buf in enumerate(pool.imap(render.frame, range(nframes), chunksize=4)):
            ff.stdin.write(buf)
            if k % 150 == 0:
                print(f"  frame {k}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
