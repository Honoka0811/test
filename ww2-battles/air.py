# -*- coding: utf-8 -*-
"""BGM: J.S.バッハ「G線上のアリア」(管弦楽組曲第3番 BWV1068 より Air) を楽譜データから合成する。
楽譜: Mutopia Project "Air, from Suite No.3 in D" (Ross Keenum 編, Public Domain) の MIDI(assets/air-bwv1068.mid)。
トロンボーン四重奏用の4声を1オクターブ上げ、低音には原音高のチェロ/コントラバス声部を重ね、
加算合成の弦楽器風の音色(デチューン3本・遅れて掛かるビブラート・ゆっくりした立ち上がり)+ 簡易リバーブで鳴らす。
録音音源を一切使わないため、録音・演奏に関する権利は発生しない(作曲者は1750年没でパブリックドメイン)。
単体実行: python3 air.py [秒数] [出力wav]
"""
import sys, os, wave
import numpy as np
import midi_read

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
MID = os.path.join(HERE, 'assets', 'air-bwv1068.mid')

def midi_hz(n): return 440.0 * 2 ** ((n - 69) / 12)

def string_note(f, dur, rng, bright=1.0):
    rel = 0.35
    n = int((dur + rel) * SR); t = np.arange(n) / SR
    # ビブラート: 0.25秒後から徐々に掛かる
    vd = np.clip((t - 0.25) / 0.6, 0, 1)
    vib = 1 + 0.0045 * vd * np.sin(2 * np.pi * 5.3 * t + rng.uniform(0, 6.28))
    sig = np.zeros(n, dtype=np.float32)
    nh = max(1, min(14, int(9000 / f)))
    for det in (-0.0035, 0.0, 0.0038):
        ph = 2 * np.pi * f * (1 + det) * np.cumsum(vib) / SR + rng.uniform(0, 6.28)
        for h in range(1, nh + 1):
            amp = (1.0 / h) * np.exp(-(h - 1) * 0.22 / bright)   # ノコギリ波を丸めた倍音構成
            sig += amp * np.sin(h * ph)
    # 弓の立ち上がり・弓圧のゆらぎ・リリース
    a = min(0.12 + 0.04 * (f < 200), dur * 0.5)
    env = np.ones(n, dtype=np.float32)
    na = int(a * SR); env[:na] = (np.linspace(0, 1, na) ** 1.6)
    swell = 1 + 0.08 * np.sin(np.pi * np.clip(t / max(dur, 0.1), 0, 1))
    env *= swell
    nr = int(rel * SR); ne = int(dur * SR)
    env[ne:] = np.linspace(1, 0, n - ne) ** 2 * env[ne - 1] if ne > 0 else 0
    return (sig * env / 3).astype(np.float32)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    # 1次IIR をブロック単位の畳み込みで近似(指数カーネル)
    k = int(SR * 5 / (2 * np.pi * fc)) + 1
    ker = (1 - a) * a ** np.arange(k)
    return np.convolve(x, ker)[:len(x)].astype(np.float32)

def reverb(x, mix=0.32):
    wet = sum(comb(x, d, g) for d, g in ((1687, 0.80), (1999, 0.79), (2371, 0.78), (2767, 0.77), (3187, 0.75)))
    wet = lowpass(wet / 5, 3500)
    return (1 - mix) * x + mix * wet

def generate(total, bpm=None, seed=3, fade_in=1.5, fade_out=3.0):
    notes, ppq, _ = midi_read.read(MID)
    end_beats = max(s + d for s, d, *_ in notes) / ppq
    if bpm is None:  # 指定が無ければ、曲の終わりが動画の終わりに来るテンポ
        bpm = end_beats / (total - 0.6) * 60
    spb = 60.0 / bpm
    rng = np.random.default_rng(seed)
    n = int(total * SR) + SR * 2
    buf = np.zeros(n, dtype=np.float32)
    for s, d, p, v, tr in notes:
        st, du = s / ppq * spb, max(d / ppq * spb, 0.12)
        if st >= total: continue   # 動画より後ろの音符は鳴らさない(曲の途中でフェードアウト)
        layers = [(p + 12, 0.55)]
        if p < 55: layers.append((p, 0.42))           # 低音はチェロ/コントラバスで重ねる
        for q, g in layers:
            x = string_note(midi_hz(q), du, rng, bright=0.8 if q < 60 else 1.0) * g * (0.6 + 0.4 * v / 127)
            i = int(st * SR); e = min(i + len(x), n)
            buf[i:e] += x[:e - i]
    buf = lowpass(buf, 5200)
    buf = reverb(buf)[:int(total * SR)]
    t = np.arange(len(buf)) / SR
    buf *= np.clip(t / fade_in, 0, 1) * np.clip((total - t) / fade_out, 0, 1)
    buf /= np.max(np.abs(buf)) + 1e-9
    print(f'air: {bpm:.1f} BPM, {end_beats:.0f} beats')
    return buf * 0.9

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'bgm.wav')
    x = generate(total)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out)
