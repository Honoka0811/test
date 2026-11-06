"""YouTube Shorts 生成スクリプト: 「どの色が最初に脱出する？」

回転するリングの中で 5 色のボールが跳ね回り、隙間から脱出した順に順位が付く
物理シミュレーション動画 (1080x1920 / 60fps / 音付き) を生成する。

使い方:
    python3 make_short.py --search      # 展開が面白くなる乱数シードを探す
    python3 make_short.py --seed 123    # そのシードで動画を書き出す
"""
import argparse
import math
import os
import subprocess
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------- 設定 ----------------
W, H = 1080, 1920
FPS = 60
SUB = 8                      # 1 フレームあたりの物理サブステップ
DT = 1.0 / (FPS * SUB)
SS = 2                       # 描画のスーパーサンプリング倍率
CX, CY = W / 2, 980          # リング中心
R = 400                      # リング内径
BR = 34                      # ボール半径
GAP = math.radians(28)       # 隙間の角度幅
OMEGA = math.radians(70)     # リング回転速度 [rad/s]
G = 1500.0                   # 重力 [px/s^2]
MAX_T = 58.0                 # 最大尺 [s]
OUTRO = 3.5                  # 全員脱出後の余韻 [s]
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
HERE = os.path.dirname(os.path.abspath(__file__))

BALLS = [  # 表示名, 色
    ("赤", (255, 70, 90)),
    ("青", (60, 150, 255)),
    ("緑", (60, 230, 120)),
    ("黄", (255, 215, 50)),
    ("紫", (190, 90, 255)),
]
N = len(BALLS)


# ---------------- 物理 ----------------
def simulate(seed):
    rng = np.random.default_rng(seed)
    pos = np.zeros((N, 2))
    for i in range(N):  # 重ならない初期配置
        while True:
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0, R - BR - 40)
            p = np.array([math.cos(a) * d, math.sin(a) * d])
            if all(np.linalg.norm(p - pos[j]) > 2 * BR + 10 for j in range(i)):
                pos[i] = p
                break
    ang = rng.uniform(0, 2 * math.pi, N)
    vel = np.stack([np.cos(ang), np.sin(ang)], 1) * rng.uniform(700, 900, (N, 1))
    state = np.zeros(N, int)   # 0=中, 1=脱出中/脱出済み
    rank = []                  # (ball index, time)
    events = []                # (time, kind, ball)  kind: wall/ball/escape
    frames = []
    rot0 = rng.uniform(0, 2 * math.pi)
    t, end_t, step = 0.0, None, 0
    while True:
        if step % SUB == 0:
            frames.append((t, pos.copy(), state.copy(), list(rank)))
            if end_t is not None and t >= end_t:
                break
            if t >= MAX_T:
                break
        rot = rot0 + OMEGA * t
        vel[:, 1] += G * DT
        pos += vel * DT
        # ボール同士
        for i in range(N):
            for j in range(i + 1, N):
                if state[i] or state[j]:
                    continue
                d = pos[j] - pos[i]
                dist = np.linalg.norm(d)
                if 0 < dist < 2 * BR:
                    n = d / dist
                    rv = np.dot(vel[i] - vel[j], n)
                    if rv > 0:
                        vel[i] -= rv * n
                        vel[j] += rv * n
                        events.append((t, "ball", i))
                    over = 2 * BR - dist
                    pos[i] -= n * over / 2
                    pos[j] += n * over / 2
        # 壁
        for i in range(N):
            if state[i]:
                continue
            dist = np.linalg.norm(pos[i])
            if dist > R - BR:
                a = math.atan2(pos[i][1], pos[i][0])
                rel = (a - rot + math.pi) % (2 * math.pi) - math.pi
                if abs(rel) < GAP / 2 - BR / R:
                    state[i] = 1
                    rank.append((i, t))
                    events.append((t, "escape", i))
                    if len(rank) == N:
                        end_t = t + OUTRO
                    continue
                n = pos[i] / dist
                vn = np.dot(vel[i], n)
                if vn > 0:
                    vel[i] -= 2 * vn * n
                    # 少しだけ接線方向にランダム性 → 永久周期軌道を防ぐ
                    tng = np.array([-n[1], n[0]])
                    vel[i] += tng * rng.normal(0, 25)
                    sp = np.linalg.norm(vel[i])
                    events.append((t, "wall", i))
                    if sp > 1800:
                        vel[i] *= 1800 / sp
                pos[i] = n * (R - BR)
        t += DT
        step += 1
    return dict(frames=frames, events=events, rank=rank, rot0=rot0)


def score(sim):
    """展開の面白さ: 1位は早すぎず、全員が尺内に脱出し、間隔がばらける。"""
    times = [t for _, t in sim["rank"]]
    if len(times) < N:
        return -1, times
    first, last = times[0], times[-1]
    if first < 4 or last > 50 or last < 25:
        return -1, times
    gaps = np.diff([0] + times)
    # 最後の 2 人の一騎打ちが長いと盛り上がる
    return float(min(gaps[1:]) + 0.3 * (times[-1] - times[-2])), times


# ---------------- 描画 ----------------
_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size * SS)
    return _fonts[size]


def S(v):
    return v * SS


def text_c(d, xy, s, size, fill, stroke=0, sfill=(0, 0, 0)):
    d.text((S(xy[0]), S(xy[1])), s, font=font(size), fill=fill, anchor="mm",
           stroke_width=S(stroke), stroke_fill=sfill)


def draw_frame(args):
    fi, t, pos, state, rank, hist, rot0, flashes = args
    img = Image.new("RGB", (S(W), S(H)), (12, 12, 22))
    d = ImageDraw.Draw(img, "RGBA")
    # 背景のうっすらグリッド
    for x in range(0, W, 60):
        d.line([(S(x), 0), (S(x), S(H))], fill=(255, 255, 255, 8), width=S(1))
    for y in range(0, H, 60):
        d.line([(0, S(y)), (S(W), S(y))], fill=(255, 255, 255, 8), width=S(1))

    # 見出し
    text_c(d, (W / 2, 150), "どの色が最初に", 84, (255, 255, 255), 6)
    text_c(d, (W / 2, 250), "脱出する？", 104, (255, 230, 80), 7)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    if not rank:
        text_c(d, (W / 2, 355), "▼ コメントで予想してね ▼", 46,
               (255, 255, 255, int(160 + 95 * pulse)), 3)
    else:
        text_c(d, (W / 2, 355), f"TIME {t:5.1f}s", 46, (200, 200, 220), 3)

    # リング
    rot = rot0 + OMEGA * t
    ring_r = R + 10
    box = [S(CX - ring_r), S(CY - ring_r), S(CX + ring_r), S(CY + ring_r)]
    start = math.degrees(rot + GAP / 2)
    end = math.degrees(rot - GAP / 2) + 360
    hue = (t * 40) % 360
    rc = hsv(hue, 0.6, 1.0)
    for w, a in [(46, 30), (34, 50), (24, 90)]:  # グロー
        gb = [box[0] - S(w // 2 - 10), box[1] - S(w // 2 - 10),
              box[2] + S(w // 2 - 10), box[3] + S(w // 2 - 10)]
        d.arc(gb, start, end, fill=rc + (a,), width=S(w))
    d.arc(box, start, end, fill=rc + (255,), width=S(16))

    # 軌跡
    for k, ph in enumerate(hist):
        a = int(110 * (k + 1) / len(hist))
        rr = BR * (0.35 + 0.55 * (k + 1) / len(hist))
        for i in range(N):
            x, y = CX + ph[i][0], CY + ph[i][1]
            d.ellipse([S(x - rr), S(y - rr), S(x + rr), S(y + rr)],
                      fill=BALLS[i][1] + (a // 3,))
    # ボール
    for i in range(N):
        x, y = CX + pos[i][0], CY + pos[i][1]
        if y > H + BR * 2:
            continue
        c = BALLS[i][1]
        fl = flashes[i]
        gr = BR + 14 + 20 * fl
        d.ellipse([S(x - gr), S(y - gr), S(x + gr), S(y + gr)], fill=c + (int(50 + 120 * fl),))
        d.ellipse([S(x - BR), S(y - BR), S(x + BR), S(y + BR)], fill=c,
                  outline=(255, 255, 255), width=S(4))
        text_c(d, (x, y + 1), BALLS[i][0], 34, (255, 255, 255), 3, (0, 0, 0))

    # 順位表
    top = 1500
    d.rounded_rectangle([S(90), S(top), S(W - 90), S(top + 330)], radius=S(30),
                        fill=(255, 255, 255, 18), outline=(255, 255, 255, 60), width=S(3))
    labels = ["1位", "2位", "3位", "4位", "5位"]
    for k in range(N):
        cx = 90 + (W - 180) * (k + 0.5) / N
        text_c(d, (cx, top + 60), labels[k], 40, (255, 230, 80) if k == 0 else (220, 220, 230), 2)
        if k < len(rank):
            i, rt = rank[k]
            age = t - rt
            sc = 1 + max(0, 0.6 - age) * 1.2  # ポップイン
            rr = 50 * sc
            yy = top + 175
            d.ellipse([S(cx - rr), S(yy - rr), S(cx + rr), S(yy + rr)], fill=BALLS[i][1],
                      outline=(255, 255, 255), width=S(4))
            text_c(d, (cx, yy + 1), BALLS[i][0], int(46 * sc), (255, 255, 255), 3)
            text_c(d, (cx, top + 280), f"{rt:.1f}s", 32, (200, 200, 215), 2)
        else:
            d.ellipse([S(cx - 50), S(top + 125), S(cx + 50), S(top + 225)],
                      outline=(255, 255, 255, 70), width=S(3))
            text_c(d, (cx, top + 176), "?", 50, (255, 255, 255, 90))

    # 1 位決定の演出
    if rank:
        i0, t0 = rank[0]
        age = t - t0
        if 0 <= age < 2.2:
            a = int(255 * min(1, (2.2 - age) * 2))
            sc = 1 + max(0, 0.3 - age) * 2
            text_c(d, (W / 2, 468), f"{BALLS[i0][0]}が1位で脱出！", int(80 * sc),
                   BALLS[i0][1] + (a,), 6, (0, 0, 0, a))
    if len(rank) == N:
        age = t - rank[-1][1]
        if age > 0.3:
            a = int(255 * min(1, (age - 0.3) * 3))
            text_c(d, (W / 2, 468), "予想は当たった？", 84, (255, 255, 255, a), 6, (0, 0, 0, a))
            text_c(d, (W / 2, 1390), "高評価＆チャンネル登録で次回も！", 50,
                   (255, 230, 80, a), 4, (0, 0, 0, a))

    return np.asarray(img.reduce(SS)).tobytes()


def hsv(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h / 360, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


# ---------------- 音 ----------------
SR = 44100
SCALE = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]  # メジャーペンタトニック


def tone(freq, dur, vol, decay=10.0, kind="pluck"):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    env = np.exp(-tt * decay) * np.minimum(1, tt * 400)
    if kind == "pluck":
        w = np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(4 * np.pi * freq * tt) \
            + 0.15 * np.sin(6 * np.pi * freq * tt)
    else:
        w = np.sin(2 * np.pi * freq * tt)
    return w * env * vol


def make_audio(sim, dur, path):
    buf = np.zeros(int(SR * (dur + 2)))
    note = 0
    last_wall = -1
    for t, kind, i in sim["events"]:
        s = int(t * SR)
        if kind == "wall":
            if t - last_wall < 0.03:
                continue
            last_wall = t
            semi = SCALE[note % len(SCALE)] + 12 * ((note // len(SCALE)) % 2)
            note += 1
            f = 261.63 * 2 ** (semi / 12)
            x = tone(f, 0.5, 0.22)
        elif kind == "ball":
            x = tone(880, 0.12, 0.08, 30, "sine")
        else:  # escape: 上昇アルペジオ
            x = np.zeros(int(SR * 1.0))
            for k, semi in enumerate([0, 4, 7, 12, 16]):
                y = tone(523.25 * 2 ** (semi / 12), 0.6, 0.25, 6)
                o = int(k * 0.06 * SR)
                x[o:o + len(y)] += y[:len(x) - o]
        buf[s:s + len(x)] += x[:len(buf) - s]
    buf = buf[:int(SR * dur)]
    buf = np.tanh(buf * 1.2) * 0.8  # ソフトクリップ
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------- 出力 ----------------
def render(seed, out):
    sim = simulate(seed)
    frames = sim["frames"]
    dur = len(frames) / FPS
    print(f"seed={seed} 尺={dur:.1f}s 順位={[(BALLS[i][0], round(t, 1)) for i, t in sim['rank']]}")
    # 衝突フラッシュ量
    flash_t = [[] for _ in range(N)]
    for t, kind, i in sim["events"]:
        if kind == "wall":
            flash_t[i].append(t)
    jobs = []
    for fi, (t, pos, state, rank) in enumerate(frames):
        hist = [frames[max(0, fi - k)][1] for k in range(12, 0, -2)]
        fl = []
        for i in range(N):
            recent = [t - ft for ft in flash_t[i] if 0 <= t - ft < 0.25]
            fl.append(max([1 - r / 0.25 for r in recent], default=0.0))
        jobs.append((fi, t, pos, state, rank, hist, sim["rot0"], fl))

    wav = os.path.join(HERE, "_audio.wav")
    make_audio(sim, dur, wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, b in enumerate(pool.imap(draw_frame, jobs, chunksize=8)):
            ff.stdin.write(b)
            if k % 300 == 0:
                print(f"  frame {k}/{len(jobs)}", flush=True)
            if k == int(len(jobs) * 0.0) + 30:  # サムネ候補: 開始 0.5 秒
                Image.frombytes("RGB", (W, H), b).save(os.path.join(HERE, "thumbnail.png"))
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    return sim


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "short.mp4"))
    a = ap.parse_args()
    if a.search:
        best = []
        for s in range(300):
            sc, times = score(simulate(s))
            if sc > 0:
                best.append((sc, s, [round(x, 1) for x in times]))
        for b in sorted(best, reverse=True)[:8]:
            print(b)
    else:
        render(a.seed, a.out)
