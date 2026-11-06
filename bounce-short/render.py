"""フレームを描画して ffmpeg にパイプし、バウンド音(自作合成)を付けて mp4 にする。"""
import colorsys, math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sim import simulate, FPS, CX, CY, R, R0, FILL

W, H = 1080, 1920
SR = 48000
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f_big = ImageFont.truetype(BOLD, 88)
f_mid = ImageFont.truetype(BOLD, 56)
f_hud = ImageFont.truetype(BOLD, 64)
f_end = ImageFont.truetype(BOLD, 150)

frames, bounces, done_at = simulate()
N = len(frames)
dur = N / FPS


def hue_rgb(h, s=0.85, v=1.0):
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1.0, s, v))


def text_c(d, y, s, font, fill, stroke=6):
    w = d.textlength(s, font=font)
    d.text(((W - w) / 2, y), s, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


# ---------- 音 ----------
def synth_audio(path):
    audio = np.zeros(int((dur + 1) * SR))
    scale = [0, 2, 4, 7, 9]  # ペンタトニック(どの順でも濁らない)
    motif = [0, 2, 4, 2, 5, 4, 3, 1]  # 自作モチーフ(音階インデックス)
    for i, (t, n, r, _, _) in enumerate(bounces):
        prog = (r - R0) / (FILL - R0)
        octave = int(prog * 2.2)
        deg = motif[i % len(motif)] + octave * 5
        semi = scale[deg % 5] + 12 * (deg // 5)
        f = 261.63 * 2 ** (semi / 12)
        L = int(SR * 0.9)
        tt = np.arange(L) / SR
        env = np.exp(-tt * 5.5) * (1 - np.exp(-tt * 400))
        tone = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)
                + 0.12 * np.sin(6 * np.pi * f * tt)) * env
        click = np.random.default_rng(i).normal(0, 1, L) * np.exp(-tt * 180) * 0.25
        s = int(t * SR)
        seg = (tone + click) * 0.32
        audio[s:s + L] += seg[: len(audio) - s]
    if done_at:  # 完成時の和音
        L = int(SR * 3.5)
        tt = np.arange(L) / SR
        env = np.exp(-tt * 1.1) * (1 - np.exp(-tt * 60))
        chord = sum(np.sin(2 * np.pi * 261.63 * 2 ** (k / 12) * tt) for k in (12, 16, 19, 24, 28))
        s = int(done_at * SR)
        audio[s:s + L] += (chord * env * 0.12)[: len(audio) - s]
    # 簡易リバーブ
    for dly, g in ((0.071, 0.3), (0.113, 0.22), (0.179, 0.15)):
        k = int(dly * SR)
        audio[k:] += audio[:-k] * g
    audio /= max(1e-9, np.abs(audio).max()) / 0.9
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


# ---------- 映像 ----------
def render(path):
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "18", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    trail = np.zeros((H, W, 3), np.float32)
    bi = 0
    flash = 0.0
    yy, xx = np.mgrid[0:H, 0:W]
    bg = np.stack([np.full((H, W), 8), np.full((H, W), 8), 14 + 10 * (yy / H)], -1).astype(np.float32)
    for fi, (x, y, r, n) in enumerate(frames):
        t = fi / FPS
        while bi < len(bounces) and bounces[bi][0] <= t:
            flash = 1.0; bi += 1
        prog = (r - R0) / (FILL - R0)
        hue = t * 0.05
        col = hue_rgb(hue)
        # 残像レイヤー(輪郭を毎フレーム重ね、徐々に消す)
        trail *= 0.90
        layer = Image.new("RGB", (W, H))
        ld = ImageDraw.Draw(layer)
        ld.ellipse([x - r, y - r, x + r, y + r], outline=col, width=5)
        trail = np.maximum(trail, np.asarray(layer, np.float32) * 0.85)
        img = Image.fromarray(np.clip(bg + trail, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        # 外枠(バウンドの瞬間に光る)
        ring = hue_rgb(hue + 0.5, 0.7, 0.6 + 0.4 * flash)
        rw = int(8 + 10 * flash)
        d.ellipse([CX - R - rw, CY - R - rw, CX + R + rw, CY + R + rw], outline=ring, width=rw)
        # ボール本体
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        hr = r * 0.35
        d.ellipse([x - r * 0.45 - hr / 2, y - r * 0.45 - hr / 2, x - r * 0.45 + hr / 2, y - r * 0.45 + hr / 2],
                  fill=hue_rgb(hue, 0.3, 1.0))
        # 上部フック
        text_c(d, 190, "EVERY BOUNCE", f_big, (255, 255, 255))
        text_c(d, 300, "= BIGGER BALL", f_big, (255, 220, 60))
        if done_at is None or t < done_at:
            text_c(d, 430, "Will it fill the circle?", f_mid, (200, 200, 220), 4)
        # 下部HUD
        text_c(d, 1530, f"BOUNCES: {n}", f_hud, (255, 255, 255))
        bw, bx, by = 760, (W - 760) // 2, 1640
        d.rounded_rectangle([bx, by, bx + bw, by + 46], 23, outline=(255, 255, 255), width=4)
        d.rounded_rectangle([bx + 6, by + 6, bx + 6 + max(34, (bw - 12) * prog), by + 40], 17, fill=col)
        text_c(d, 1710, f"{int(prog * 100)}%", f_mid, (255, 255, 255), 4)
        if done_at is not None and t >= done_at:
            k = min(1.0, (t - done_at) / 0.25)
            text_c(d, CY - 90, "FILLED!", f_end, (255, 255, 255), int(10 * k))
            if t > done_at + 1.2:
                text_c(d, 430, f"{len(bounces)} bounces. Watch again?", f_mid, (255, 220, 60), 4)
        flash *= 0.80
        ff.stdin.write(img.tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{N}", file=sys.stderr)
    ff.stdin.close(); ff.wait()


if __name__ == "__main__":
    synth_audio("output/bounce.wav")
    render("output/video_silent.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "output/video_silent.mp4", "-i", "output/bounce.wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "output/every_bounce_bigger.mp4"], check=True)
    print("done", dur, "sec")
