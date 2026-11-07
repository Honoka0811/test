# -*- coding: utf-8 -*-
"""視聴者を引き込む系のアップテンポBGMをプログラムで合成する(外部音源不要・権利フリー)。
A マイナー / 128 BPM。サイドチェインの効いたシンセベース + 4つ打ちキック + クラップ + ハイハット
+ スーパーソウのコードスタブ + 16分アルペジオ(ディレイ付き) + ライザー/インパクト。
動画のシーン構成(narrate.py / render.html)に合わせてセクションが切り替わる。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 128
BEAT = 60.0 / BPM
BAR = BEAT * 4

# セクション(開始秒, 種別)  render.html の SCENES に対応
SECTIONS = [
    (0.0, 'intro'),      # フック: ベースの脈動 + ハット + ライザー
    (5.0, 'build'),      # キック投入、後半でスネアロール
    (11.5, 'drop'),      # フル
    (30.0, 'break'),     # 一旦キックを抜いて緊張 → 33.5 で復帰
    (39.5, 'drop'),      # フル
    (50.0, 'outro'),     # パッド + アルペジオ、フェード
]
TOTAL_DEFAULT = 57.5

# コード進行: Am - F - C - G(1小節ずつ)
PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [45, 41, 48, 43]
ARP = [[0, 1, 2, 1, 0, 2, 1, 2], [0, 2, 1, 2, 0, 1, 2, 1]]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def lp(x, fc, order=2): return sosfilt(butter(order, fc / (SR / 2), 'low', output='sos'), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc / (SR / 2), 'high', output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x)
def add(buf, start_s, sig, gain=1.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * gain
def section_at(t):
    cur = SECTIONS[0][1]
    for s, k in SECTIONS:
        if t >= s - 1e-6: cur = k
    return cur
def saw(f, n, det=0.0):
    t = np.arange(n) / SR
    return (2 * ((f * (1 + det) * t) % 1.0) - 1).astype(np.float32)

# ---------- 音色 ----------
def kick(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 48 + 120 * np.exp(-t / 0.045)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    click = np.random.default_rng(1).standard_normal(n) * np.exp(-t / 0.004) * 0.6
    return np.tanh(1.8 * (body + click)).astype(np.float32)

def clap(rng, dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.zeros(n)
    for k, off in enumerate((0, 0.011, 0.022, 0.033)):
        env += np.where(t >= off, np.exp(-(t - off) / (0.009 if k < 3 else 0.09)), 0)
    return (bp(rng.standard_normal(n), 900, 4500) * env * 0.7).astype(np.float32)

def hat(rng, dur=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    return (hp(rng.standard_normal(n), 7500, 4) * np.exp(-t / (dur / 3.5)) * 0.5).astype(np.float32)

def bass_note(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = saw(f, n) + 0.5 * saw(f / 2, n) + 0.3 * np.sin(2 * np.pi * f / 2 * t)
    x = 0.5 * lp(x, 700) * np.exp(-t / 0.08) + 0.5 * lp(x, 160)   # 鳴り始めだけ明るく
    env = np.ones(n); a = int(0.004 * SR); r = int(0.03 * SR)
    env[:a] = np.linspace(0, 1, a); env[-r:] = np.linspace(1, 0, r)
    return (x * env).astype(np.float32)

def stab(notes, dur, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for m in notes:
        for det in (-0.006, 0.0, 0.006):
            x += saw(midi(m), n, det) / 3
    x = lp(x, 1400 * bright + 400 * np.exp(-t[0]))
    env = np.exp(-t / (dur * 0.6)); a = int(0.005 * SR); env[:a] *= np.linspace(0, 1, a)
    return (x * env * 0.5).astype(np.float32)

def pad(notes, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for m in notes:
        for det in (-0.004, 0.004):
            x += saw(midi(m), n, det) / 2
    x = lp(x, 900)
    env = np.ones(n); a = int(0.4 * SR); r = int(0.4 * SR)
    env[:a] = np.linspace(0, 1, a); env[-r:] = np.linspace(1, 0, r)
    return (x * env * 0.35).astype(np.float32)

def pluck(f, dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.15 * np.sin(2 * np.pi * 3 * f * t)
    return (x * np.exp(-t / 0.11)).astype(np.float32)

def riser(dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR; p = t / dur
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    # 周波数の上がるバンドパスを区切って近似
    for i in range(8):
        a, b = int(n * i / 8), int(n * (i + 1) / 8)
        fc = 300 * (1 + 3.5 * (i + 0.5) / 8)
        out[a:b] = bp(noise, fc, fc * 2.2)[a:b]
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (p * 2.5)) / SR) * 0.35
    return ((out * 0.8 + tone) * p ** 1.6).astype(np.float32)

def impact(rng, dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.35)
    noise = lp(rng.standard_normal(n), 2500) * np.exp(-t / 0.18)
    return (np.tanh(1.5 * (sub + 0.6 * noise))).astype(np.float32)

def delay(x, time_s, fb=0.4, mix=0.35):
    d = int(time_s * SR); y = x.copy()
    for s in range(d, len(y), d):
        e = min(s + d, len(y)); y[s:e] += fb * y[s - d:e - d]
    return x + mix * (y - x)

# ---------- 組み立て ----------
def generate(total=TOTAL_DEFAULT, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    drums = np.zeros(n, np.float32); bass = np.zeros(n, np.float32); chords = np.zeros(n, np.float32)
    lead = np.zeros(n, np.float32); fx = np.zeros(n, np.float32)
    kick_env_times = []
    K = kick(); HAT = hat(rng); HATO = hat(rng, 0.16)
    nbars = int(np.ceil(total / BAR)) + 1
    for b in range(nbars):
        t0 = b * BAR; chord = PROG[b % 4]; root = ROOTS[b % 4]
        for beat in range(4):
            tb = t0 + beat * BEAT; sec = section_at(tb)
            if tb >= total: break
            kick_on = sec in ('build', 'drop') or (sec == 'break' and tb >= 33.5) or (sec == 'outro' and tb < 54)
            if kick_on and not (sec == 'break' and beat % 2 == 1):
                add(drums, tb, K, 1.0 if sec != 'outro' else 0.6); kick_env_times.append(tb)
            if sec == 'drop' and beat in (1, 3):
                add(drums, tb, clap(rng), 0.9)
            # ハット: 8分、ドロップでは 16 分
            div = 4 if sec == 'drop' else 2
            if sec != 'outro' or tb < 54:
                for k in range(div):
                    th = tb + k * BEAT / div
                    add(drums, th, HATO if (div == 2 and k == 1) or (div == 4 and k == 2) else HAT,
                        (0.55 if k == 0 else 0.35) * (0.7 if sec in ('intro', 'break') else 1.0))
            # ベース: 8分で刻む(ブレイク前半は抜く)
            if not (sec == 'break' and tb < 33.5):
                for k in range(2):
                    m = root if not (beat == 3 and k == 1) else root + 12
                    add(bass, tb + k * BEAT / 2, bass_note(midi(m), BEAT / 2 * 0.9), 0.9 if sec != 'intro' else 0.7)
            # コード: 裏拍のスタブ(ドロップ/ビルド)、ブレイク/アウトロはパッド
            if sec in ('drop', 'build') and beat in (0, 2):
                add(chords, tb + BEAT / 2, stab([m + 12 for m in chord], BEAT * 0.9), 0.8)
            # リード: 16 分アルペジオ(ドロップ)
            if sec == 'drop' or (sec == 'outro'):
                pat = ARP[b % 2]
                for k in range(4):
                    idx = pat[(beat * 4 + k) % 8]
                    m = chord[idx] + 24 + (12 if (b % 4 == 3 and beat == 3) else 0)
                    add(lead, tb + k * BEAT / 4, pluck(midi(m)), 0.5 if sec == 'drop' else 0.35)
        sec0 = section_at(t0)
        if sec0 in ('break', 'intro', 'outro'):
            add(chords, t0, pad([m + 12 for m in chord], BAR + 0.3), 0.9)
    # ビルド末尾のスネアロール(9.3〜11.5)、ブレイク末尾(36.0〜37.3)、drop2 前(47.5〜49.5 は無し)
    for a, b_ in ((9.3, 11.5), (36.0, 37.3)):
        t = a; step = BEAT / 2
        while t < b_:
            add(drums, t, clap(rng, 0.15), 0.4 + 0.5 * (t - a) / (b_ - a))
            step = max(BEAT / 16, step * 0.86); t += step
    # ライザー: 各リビール前
    for a, b_ in ((2.0, 5.0), (8.3, 11.5), (25.0, 27.0), (35.0, 37.3), (41.5, 42.9), (50.5, 52.0)):
        add(fx, a, riser(b_ - a, rng), 0.55)
    # インパクト: 大きな見せ場
    for t in (0.05, 5.0, 11.5, 12.55, 27.0, 30.0, 37.3, 39.5, 42.9, 52.0):
        add(fx, t, impact(rng), 0.9 if t in (0.05, 12.55, 37.3) else 0.55)
    # サイドチェイン(キックのたびにベース/コード/リードを沈める)
    sc = np.ones(n, np.float32)
    dip = np.linspace(0.25, 1.0, int(0.22 * SR)) ** 1.6
    for t in kick_env_times:
        s = int(t * SR); e = min(s + len(dip), n); sc[s:e] = np.minimum(sc[s:e], dip[:e - s])
    lead = delay(lead, BEAT * 0.75, 0.42, 0.4)
    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.95 * norm(drums) + 0.55 * norm(bass) * sc + 0.45 * norm(chords) * (0.6 + 0.4 * sc) + 0.4 * norm(lead) * (0.7 + 0.3 * sc) + 0.6 * norm(fx)
    # 軽いコンプ風サチュレーション
    mix = np.tanh(1.3 * mix / (np.max(np.abs(mix)) + 1e-9))
    fade_in = int(0.3 * SR); fade_out = int(3.0 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in); mix[-fade_out:] *= np.linspace(1, 0, fade_out) ** 1.5
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else TOTAL_DEFAULT
    out = sys.argv[2] if len(sys.argv) > 2 else 'output/bgm.wav'
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.1f}s')
