# -*- coding: utf-8 -*-
"""J.S.バッハ「管弦楽組曲第3番 BWV1068 より Air(G線上のアリア)」を弦楽合奏風に合成する。
楽譜データ: Mutopia Project のトロンボーン四重奏版 MIDI(assets/air-tromb.mid, パブリックドメイン)。
音源はすべて numpy で合成(既存の録音は使わない)ので、作曲・楽譜・音源ともに権利フリー。
曲全体(76拍)を動画の長さに合わせたテンポで演奏し、最後の2小節でリタルダンドして主和音で終わる。
単体実行: python3 bgm_air.py [秒数] [出力wav]
"""
import os, sys, wave
import numpy as np
import mido

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
MID = os.path.join(HERE, 'assets', 'air-tromb.mid')

# 声部ごとの設定: (移調[半音], 音量, パン(-1左..1右), ビブラート深さ, 音色の明るさ)
# 原曲はトロンボーン用に旋律が1オクターブ下がっているので、上2声を +12 して弦の音域に戻す
VOICES = {
    'tenorOne': (12, 1.00, -0.30, 0.0050, 1.00),   # 第1ヴァイオリン(旋律)
    'alto':     (12, 0.42,  0.30, 0.0040, 0.90),   # 第2ヴァイオリン
    'bass':     (0,  0.40,  0.15, 0.0035, 0.70),   # ヴィオラ〜低音
    'tenorTwo': (0,  0.46,  0.05, 0.0030, 0.65),   # チェロ(オクターブで歩く低音)
}

def load_notes():
    m = mido.MidiFile(MID); tpb = m.ticks_per_beat
    notes = []
    for tr in m.tracks:
        if tr.name not in VOICES: continue
        T = 0; on = {}
        for x in tr:
            T += x.time
            if x.type == 'note_on' and x.velocity > 0: on[x.note] = T
            elif x.type in ('note_off', 'note_on') and x.note in on:
                s = on.pop(x.note); notes.append((tr.name, s / tpb, (T - s) / tpb, x.note))
    return notes

BPM = float(os.environ.get('BGM_BPM', '32'))   # 演奏テンポ(4分音符/分)。8分音符=64 程度の、一般的な演奏に近いゆったりした速さ

def beat_to_sec_fn(total, end_hold=4.6, rit_beats=8, rit_amount=0.72):
    """拍→秒の対応。最終和音(74拍目)が total-end_hold 秒に来るよう基本テンポを決め、最後 rit_beats 拍でリタルダンド"""
    last = 74.0
    rit_start = last - rit_beats
    # リット区間では1拍の長さが 1 → 1/rit_amount 倍まで線形に伸びる
    rit_len = rit_beats * (1 + 1 / rit_amount) / 2
    spb = max(60 / BPM, (total - end_hold) / (rit_start + rit_len))   # 遅くはしても、速くはしない
    def f(b):
        if b <= rit_start: return b * spb
        x = min(b, last) - rit_start
        stretch = 1 + (1 / rit_amount - 1) * x / rit_beats
        sec = rit_start * spb + spb * x * (1 + stretch) / 2
        if b > last: sec += (b - last) * spb / rit_amount
        return sec
    return f, 60 / spb

def wavetable(f0, bright):
    """帯域制限したノコギリ波(弦の音色の素)。高次倍音はやや弱めて柔らかく"""
    N = 2048
    ph = np.arange(N) / N * 2 * np.pi
    tab = np.zeros(N)
    hmax = int(min(7000, 9000 * bright) / f0)
    for h in range(1, max(2, hmax)):
        tab += np.sin(h * ph) / h ** (1.15 + 0.35 * (1 - bright))
    return tab / np.max(np.abs(tab))

def string_note(f0, dur, vib, bright, rng):
    rel = 0.35
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    tab = wavetable(f0, bright)
    for det in (-0.0035, 0.0, 0.0038):           # 3人で弾いている感じ(コーラス)
        vrate = 5.0 + rng.uniform(-0.4, 0.4)
        vdepth = vib * np.clip((t - 0.18) / 0.35, 0, 1)   # ビブラートは少し遅れてかかる
        fi = f0 * (1 + det) * (1 + vdepth * np.sin(2 * np.pi * vrate * t + rng.uniform(0, 6.28)))
        phase = (np.cumsum(fi) / SR + rng.uniform(0, 1)) % 1.0
        out += np.interp(phase * 2048, np.arange(2049), np.append(tab, tab[0]))
    # 弓のエンベロープ: やわらかい立ち上がり、長い音はふくらみ、離すときはなめらかに
    att = min(0.12, dur * 0.4)
    env = np.ones(n)
    na = int(att * SR); env[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if dur > 0.8:
        k = int(dur * SR)
        env[:k] *= 0.88 + 0.12 * np.sin(np.linspace(0, np.pi, k))
    nr = int(rel * SR); k = int(dur * SR)
    env[k:] = np.linspace(1, 0, n - k) ** 2 * env[k - 1]
    return out * env / 3

def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    from scipy.signal import lfilter  # noqa
    return lfilter([1 - a], [1, -a], x)

def comb(x, delay, g):
    y = x.copy()
    for s in range(delay, len(y), delay):
        e = min(s + delay, len(y)); y[s:e] += g * y[s - delay:e - delay]
    return y

def allpass(x, delay, g=0.5):
    from scipy.signal import lfilter
    b = np.zeros(delay + 1); a = np.zeros(delay + 1)
    b[0] = -g; b[-1] = 1; a[0] = 1; a[-1] = -g
    return lfilter(b, a, x)

def reverb(x, delays, mix):
    wet = sum(comb(x, d, g) for d, g in delays) / len(delays)
    for d in (347, 113, 37):
        wet = allpass(wet, d)
    wet = onepole_lp(wet, 4500)
    return (1 - mix) * x + mix * wet

def beat_at(b2s, sec):
    b = 0.0
    while b2s(b) < sec and b < 76: b += 0.25
    return b

def generate(total, seed=3):
    rng = np.random.default_rng(seed)
    notes = load_notes()
    b2s, bpm = beat_to_sec_fn(total)
    fits = b2s(74) <= total - 2.0          # 曲の終わりまで動画に収まるか(収まらなければ途中でフェードアウト)
    notes = [x for x in notes if b2s(x[1]) < total]
    print(f'BGM: Air BWV1068  tempo {bpm:.1f} BPM, {len(notes)} notes, ' + ('full piece' if fits else f'fade out at beat {beat_at(b2s, total):.0f}/76'))
    n = int(total * SR) + SR * 3
    L = np.zeros(n); R = np.zeros(n)
    for voice, sb, db, pitch in notes:
        tr, gain, pan, vib, bright = VOICES[voice]
        p = pitch + tr
        s = b2s(sb)
        if sb >= 74: e = total - 0.6                      # 最終和音は動画の最後まで伸ばす
        else: e = b2s(sb + db)
        dur = max(0.08, (e - s) * (0.97 if db >= 1 else 0.92))
        f0 = 440 * 2 ** ((p - 69) / 12)
        sig = string_note(f0, dur, vib, bright, rng) * gain
        # 低音域はやや控えめに(こもり防止)
        if p < 50: sig *= 0.8
        # 最終和音はゆっくり減衰
        if sb >= 74: sig *= np.exp(-np.arange(len(sig)) / SR / 3.0)
        i = int(s * SR); j = min(i + len(sig), n)
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        L[i:j] += sig[:j - i] * gl; R[i:j] += sig[:j - i] * gr
    # 低音の厚み: チェロ声部の1オクターブ下を薄く重ねる(コントラバス)
    for voice, sb, db, pitch in notes:
        if voice != 'tenorTwo' or pitch >= 55: continue
        s = b2s(sb); e = (total - 0.6) if sb >= 74 else b2s(sb + db)
        sig = string_note(440 * 2 ** ((pitch - 12 - 69) / 12), max(0.08, (e - s) * 0.85), 0.002, 0.5, rng) * 0.22
        if sb >= 74: sig *= np.exp(-np.arange(len(sig)) / SR / 3.0)
        i = int(s * SR); j = min(i + len(sig), n)
        L[i:j] += sig[:j - i] * 0.7; R[i:j] += sig[:j - i] * 0.7
    L = onepole_lp(L, 6500); R = onepole_lp(R, 6500)
    L = reverb(L, ((1553, 0.80), (1877, 0.79), (2251, 0.78), (2593, 0.77)), 0.38)
    R = reverb(R, ((1613, 0.80), (1931, 0.79), (2311, 0.78), (2671, 0.77)), 0.38)
    st = np.stack([L, R], axis=1)[:int(total * SR)]
    # フェードイン/アウト
    fi = int(0.8 * SR); st[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = int((1.5 if fits else 5.0) * SR); st[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return (st / np.max(np.abs(st)) * 0.9).astype(np.float32)

def write_wav(path, st):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    total = float(sys.argv[1]) if len(sys.argv) > 1 else 80.0
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'bgm.wav')
    write_wav(out, generate(total))
    print('wrote', out)
