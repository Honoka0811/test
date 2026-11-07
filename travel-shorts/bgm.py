# -*- coding: utf-8 -*-
"""アップテンポなトロピカルハウス風BGMを numpy だけで合成する(外部音源不要・権利フリー)。
Fメジャー / 122BPM。4つ打ちキック + クラップ + ハイハット + サイドチェインの効いたベース/パッド +
スチールパン風プラック(フックのリフ) + 裏打ちコードスタブ + ライザー/クラッシュ。
generate(total, drops=[...], risers=[...], breakdown=(a,b), outro=t) でシーン切り替えに合わせた構成を作る。
単体実行: python3 bgm.py [秒数] [出力wav]
"""
import sys, wave
import numpy as np

SR = 48000
BPM = 122
BEAT = 60.0 / BPM
BAR = BEAT * 4
STEP = BEAT / 4  # 16分音符

# I–V–vi–IV (F – C – Dm – Bb)。1小節ずつ
CHORDS = [[65, 69, 72, 77], [67, 72, 76, 79], [62, 65, 69, 74], [65, 70, 74, 77]]
BASS = [41, 36, 38, 34]
# 2小節のリフ(Fメジャーペンタトニック)。(16分スロット, MIDIノート)
RIFF = [[(0, 81), (3, 84), (6, 81), (8, 79), (11, 77), (14, 79)],
        [(0, 81), (3, 84), (6, 86), (8, 84), (11, 81), (14, 79)]]

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, start_s, sig, gain=1.0):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if e > s: buf[s:e] += sig[:e - s] * gain

def lowpass_fft(x, fc, order=2):
    """静的なローパス(FFT・バターワース風振幅特性)"""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** (2 * order)), n=len(x)).astype(np.float32)

def highpass_fft(x, fc, order=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (1 - 1 / np.sqrt(1 + (f / max(fc, 1)) ** (2 * order))), n=len(x)).astype(np.float32)

def bandpass_fft(x, lo, hi):
    return highpass_fft(lowpass_fft(x, hi), lo)

def kick(dur=0.32):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 42 + 140 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.13)
    click = np.exp(-t / 0.004) * 0.6
    x = np.tanh(1.8 * (body + click))
    return x.astype(np.float32)

def clap(rng):
    n = int(0.25 * SR); t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for k, off in enumerate((0, 0.011, 0.022, 0.033)):
        s = int(off * SR); m = n - s
        x[s:] += rng.standard_normal(m).astype(np.float32) * np.exp(-np.arange(m) / SR / (0.012 if k < 3 else 0.09))
    return bandpass_fft(x, 900, 6500) * 0.9

def hat(rng, dur=0.045, open_=False):
    n = int((0.22 if open_ else dur) * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32) * np.exp(-t / (0.06 if open_ else 0.012))
    return highpass_fft(x, 7000) * 0.6

def pluck(f, dur=0.5):
    """スチールパン/マリンバ風(サイン+倍音・速い減衰)"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.18)
         + 0.45 * np.sin(2 * np.pi * f * 2.0 * t + 0.3) * np.exp(-t / 0.07)
         + 0.18 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.04)
         + 0.10 * np.sin(2 * np.pi * f * 4.2 * t) * np.exp(-t / 0.02))
    x[:48] *= np.linspace(0, 1, 48)
    return x.astype(np.float32)

def saw(f, n, t, det=0.0):
    ph = (f * (1 + det) * t) % 1.0
    return (2 * ph - 1).astype(np.float32)

def chord_stab(notes, dur=0.22):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for m in notes:
        for det in (-0.006, 0.006):
            x += saw(midi(m), n, t, det)
    x = lowpass_fft(x, 2200) * np.exp(-t / 0.09).astype(np.float32)
    x[:96] *= np.linspace(0, 1, 96)
    return x / len(notes)

def pad_bar(notes, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for m in notes:
        for det in (-0.004, 0.004):
            x += saw(midi(m), n, t, det)
    x = lowpass_fft(x, 1400)
    e = np.ones(n, dtype=np.float32); k = int(0.02 * SR); e[:k] = np.linspace(0, 1, k); e[-k:] = np.linspace(1, 0, k)
    return x * e / len(notes)

def bass_note(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = 0.9 * np.sin(2 * np.pi * f * t) + 0.5 * lowpass_fft(saw(f, n, t), 500)
    e = np.exp(-t / 0.35); k = 96; e[:k] *= np.linspace(0, 1, k); e[-k:] *= np.linspace(1, 0, k)
    return (x * e).astype(np.float32)

def riser(dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    noise = rng.standard_normal(n).astype(np.float32)
    # 時変ハイパス風: ホワイトノイズを徐々に明るく(ブロックごとにFFTフィルタ)
    out = np.zeros(n, dtype=np.float32); B = 2048
    for s in range(0, n, B):
        seg = noise[s:s + B]; uu = s / n
        out[s:s + len(seg)] = bandpass_fft(seg, 300 + 3000 * uu ** 2, 1500 + 9000 * uu)
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2.0 * u ** 2)) / SR) * 0.25
    env = (u ** 1.6).astype(np.float32)
    return ((out * 0.9 + tone) * env).astype(np.float32)

def crash(rng, dur=1.8):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32) * np.exp(-t / 0.5)
    return highpass_fft(x, 3500) * 0.8

def impact(dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 30 + 120 * np.exp(-t / 0.05)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def reverb(x, mix=0.22):
    wet = sum(comb(x, d, g) for d, g in ((1553, 0.70), (1877, 0.68), (2251, 0.66), (2999, 0.6))) / 4
    return (1 - mix) * x + mix * lowpass_fft(wet, 5000)

def echo(x, delay_s, fb=0.35, mix=0.3):
    d = int(delay_s * SR); y = comb(np.pad(x, (0, 0)), d, fb)
    return x + mix * (y - x)

def section_energy(t, drops, breakdown, outro, total):
    """0..1 のエネルギー。drops[0] 前はイントロ、breakdown 区間は抜き、outro 以降はフェード"""
    if breakdown and breakdown[0] <= t < breakdown[1]: return 0.35
    if t < drops[0]: return 0.6
    return 1.0

def generate(total, drops=(6.0,), risers=(), breakdown=None, outro=None, seed=11):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    drums = np.zeros(n, dtype=np.float32); bass = np.zeros(n, dtype=np.float32)
    lead = np.zeros(n, dtype=np.float32); stabs = np.zeros(n, dtype=np.float32)
    pad = np.zeros(n, dtype=np.float32); fx = np.zeros(n, dtype=np.float32)
    sc = np.ones(n, dtype=np.float32)  # サイドチェイン用ゲイン
    K = kick(); CL = clap(rng); HH = hat(rng); OH = hat(rng, open_=True)
    nbars = int(np.ceil(total / BAR)) + 1
    duck_n = int(0.33 * SR); duck = np.concatenate([np.full(int(0.01 * SR), 0.25), np.linspace(0.25, 1.0, duck_n - int(0.01 * SR))]).astype(np.float32)
    for b in range(nbars):
        bt = b * BAR
        ch = CHORDS[b % 4]; root = BASS[b % 4]
        en = section_energy(bt + 0.01, drops, breakdown, outro, total)
        # --- ドラム ---
        for beat in range(4):
            t0 = bt + beat * BEAT
            if t0 >= total: break
            if en >= 0.5:
                add(drums, t0, K, 1.0 if en >= 1 else 0.8)
                s = int(t0 * SR); e = min(s + duck_n, n); sc[s:e] = np.minimum(sc[s:e], duck[:e - s])
            if beat in (1, 3) and en >= 1: add(drums, t0, CL, 0.75)
            for q in range(4):
                tq = t0 + q * STEP
                if en >= 0.5 and q in (0, 2): add(drums, tq, HH, 0.35 if q == 0 else 0.55)
                if en >= 1 and q == 2: add(drums, tq, OH, 0.3)
                if en >= 1 and q in (1, 3): add(drums, tq, HH, 0.22)
        # --- ベース(8分で刻む、2拍目裏にオクターブ) ---
        if en >= 1:
            for i in range(8):
                f = midi(root + (12 if i in (3, 7) else 0))
                add(bass, bt + i * BEAT / 2, bass_note(f, BEAT / 2 * 0.95), 0.9)
        elif en >= 0.5:
            add(bass, bt, bass_note(midi(root), BAR * 0.98), 0.7)
        # --- パッド ---
        add(pad, bt, pad_bar(ch, BAR * 1.02), 0.9 if en < 1 else 0.55)
        # --- 裏打ちコードスタブ ---
        if en >= 1:
            for i in range(4):
                add(stabs, bt + i * BEAT + BEAT / 2, chord_stab([m + 12 for m in ch]), 0.55)
        # --- リフ(リード) ---
        if en >= 0.5:
            for slot, note in RIFF[b % 2]:
                # コードが Dm/Bb のとき、riff のノートが衝突しないよう維持(ペンタトニックなので概ね協和)
                add(lead, bt + slot * STEP, pluck(midi(note), 0.45), 0.8 if en >= 1 else 0.6)
        elif en >= 0.3:
            for slot, note in RIFF[b % 2][::2]:
                add(lead, bt + slot * STEP, pluck(midi(note - 12), 0.6), 0.55)
    # --- FX: ライザー → ドロップでクラッシュ+インパクト ---
    for t_end, dur in risers:
        add(fx, max(0.0, t_end - dur), riser(dur, rng), 0.5)
    for t in drops:
        add(fx, t, crash(rng), 0.7); add(fx, t, impact(), 0.9)
    lead = echo(lead, BEAT * 0.75, 0.3, 0.28)
    lead = reverb(lead, 0.18); stabs = reverb(stabs, 0.25); pad = reverb(pad, 0.3); fx = reverb(fx, 0.2)
    # サイドチェイン(ベース・パッド・スタブ・リードを少し)
    mix = (drums * 1.0 + bass * 0.8 * sc + pad * 0.45 * sc + stabs * 0.5 * sc + lead * 0.55 * (0.6 + 0.4 * sc) + fx * 0.8)
    # アウトロのフェード
    if outro is not None and outro < total:
        s = int(outro * SR); mix[s:] *= np.linspace(1, 0.0, n - s) ** 0.7
    # 軽いソフトクリップで音圧を上げる
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    return (mix / (np.max(np.abs(mix)) or 1) * 0.95).astype(np.float32)

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    out = sys.argv[2] if len(sys.argv) > 2 else 'bgm.wav'
    x = generate(total, drops=(6.0, 20.0), risers=((6.0, 1.6), (20.0, 2.0)), breakdown=(17.0, 20.0), outro=total - 3)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
