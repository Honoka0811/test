import numpy as np, json, wave
SR = 44100
TL = json.load(open('timeline.json'))
segs = {s['key']: s for s in TL['segs']}
TOTAL = TL['total']
N = int(SR * (TOTAL + 0.5))
BEAT = 60 / TL['bpm']
rng = np.random.default_rng(7)

def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def lp(x, cutoff):
    # one-pole lowpass (vectorised via cumulative filter approximation loop in chunks)
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y

from scipy.signal import butter, sosfilt  # noqa
def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)
def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype='high', fs=SR, output='sos'), x)
def lpf(x, f, order=2):
    return sosfilt(butter(order, f, btype='low', fs=SR, output='sos'), x)

def add(buf, t, sig, gain=1.0):
    i = int(t * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain

# ---------- instruments ----------
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_exp(n, 0.16)
    s[:200] += rng.normal(0, 0.3, 200) * np.linspace(1, 0, 200)
    return np.tanh(s * 1.6)
def clap():
    n = int(0.25 * SR); x = rng.normal(0, 1, n)
    e = env_exp(n, 0.07)
    for d in (0.0, 0.011, 0.022):
        k = int(d * SR); e[k:k + 300] += np.linspace(0.8, 0, 300)
    return bp(x, 900, 4000) * e * 0.9
def hat(open_=False):
    n = int((0.22 if open_ else 0.06) * SR)
    return hp(rng.normal(0, 1, n), 7000) * env_exp(n, 0.08 if open_ else 0.018) * 0.5
def snare():
    n = int(0.18 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 190 * t) * env_exp(n, 0.04)
    nz = bp(rng.normal(0, 1, n), 1500, 8000) * env_exp(n, 0.06)
    return (body * 0.6 + nz) * 0.7
def crash():
    n = int(2.5 * SR)
    return hp(rng.normal(0, 1, n), 4000) * env_exp(n, 0.7) * 0.45
def saw(freq, n, detune=(0,)):
    t = np.arange(n) / SR; out = np.zeros(n)
    for d in detune:
        f = freq * 2 ** (d / 1200)
        out += 2 * ((t * f + rng.random()) % 1) - 1
    return out / len(detune)

def midi(m): return 440 * 2 ** ((m - 69) / 12)
# Am - F - C - G  (each 1 bar = 4 beats)
CHORDS = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]

bgm_drums = np.zeros(N); bgm_bass = np.zeros(N); bgm_pad = np.zeros(N); bgm_lead = np.zeros(N)
sfx = np.zeros(N)
K, C, H, HO, SN = kick(), clap(), hat(), hat(True), snare()

drop = segs['r10']['reveal']          # 8.0
roll_s = segs['r1a']['reveal']; roll_e = segs['r1']['reveal']
outro_s = segs['outro']['reveal']; end = TOTAL

nbeats = int(TOTAL / BEAT)
for b in range(nbeats):
    t = b * BEAT
    bar = b // 4; bib = b % 4
    root, chord = CHORDS[bar % 4]
    in_roll = roll_s - 1.0 <= t < roll_e
    intro = t < drop
    outro = t >= outro_s
    # drums
    if not intro and not in_roll:
        add(bgm_drums, t, K, 0.95 if not outro else 0.7)
        if bib in (1, 3): add(bgm_drums, t, C, 0.55)
        add(bgm_drums, t + BEAT / 2, HO if bib == 3 else H, 0.55)
        add(bgm_drums, t + BEAT / 4, H, 0.18); add(bgm_drums, t + 3 * BEAT / 4, H, 0.18)
    elif intro:
        add(bgm_drums, t + BEAT / 2, H, 0.35)
        if t >= drop - 2.0:   # snare build in the last bar of intro
            for q in range(4): add(bgm_drums, t + q * BEAT / 4, SN, 0.15 + 0.4 * (t - (drop - 2)) / 2)
    # bass: offbeat 8ths with sidechain feel
    if not in_roll and t >= 2.0:
        n = int(BEAT / 2 * SR * 0.9)
        for off in (BEAT / 2,) if intro else (0.0, BEAT / 2):
            if not intro and off == 0.0: continue
            s = lpf(saw(midi(root - 12), n, (0, 7)), 500 if intro else 900) * env_exp(n, 0.12)
            add(bgm_bass, t + off, s, 0.55)
        if not intro:
            s = lpf(saw(midi(root - 12), int(BEAT / 4 * SR), (0, 7)), 900) * env_exp(int(BEAT / 4 * SR), 0.05)
            add(bgm_bass, t + 3 * BEAT / 4, s, 0.3)
    # pad (per bar)
    if bib == 0 and not in_roll:
        n = int(4 * BEAT * SR)
        p = sum(saw(midi(m), n, (-12, 0, 11)) for m in chord) / 3
        p = lpf(p, 1400 if not intro else 700)
        a = np.minimum(1, np.arange(n) / (0.08 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.1 * SR))
        add(bgm_pad, t, p * a, 0.22)
    # pluck arpeggio (16ths) after the drop
    if not intro and not in_roll:
        pat = [0, 1, 2, 1, 0, 2, 1, 2]
        for q in range(4):
            note = chord[pat[(bib * 4 + q) % 8]] + 12 + (12 if (bib * 4 + q) % 8 == 7 else 0)
            n = int(BEAT / 4 * SR)
            s = lpf(saw(midi(note), n, (0, 9)), 3200) * env_exp(n, 0.06)
            add(bgm_lead, t + q * BEAT / 4, s, 0.16 if not outro else 0.12)

# sidechain pump on bass/pad/lead after drop
tt = np.arange(N) / SR
ph = (tt % BEAT) / BEAT
pump = np.where(tt >= drop, 0.35 + 0.65 * np.minimum(1, ph / 0.45), 1.0)
music = bgm_drums + (bgm_bass + bgm_pad + bgm_lead) * pump

# drumroll + riser for #1
n_roll = int((roll_e - roll_s - 0.25) * SR)
t_ = roll_s
while t_ < roll_e - 0.25:
    prog = (t_ - roll_s) / (roll_e - roll_s)
    add(sfx, t_, SN, 0.25 + 0.6 * prog)
    t_ += BEAT / 4 if prog < 0.5 else BEAT / 8
rs = int((roll_e - roll_s - 0.25) * SR); t = np.arange(rs) / SR
riser = hp(rng.normal(0, 1, rs), 800) * (t / t[-1]) ** 2 * 0.35
riser += np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / t[-1]) ** 2) / SR) * (t / t[-1]) ** 2 * 0.12
add(sfx, roll_s, riser)
# music fade-out at end
fo = int(2.5 * SR)
music[int((end - 2.5) * SR):int(end * SR)] *= np.linspace(1, 0, fo)[:len(music[int((end - 2.5) * SR):int(end * SR)])]
music[int(end * SR):] = 0
# final chord ring
n = int(3 * SR); fin = sum(saw(midi(m), n, (-8, 0, 8)) for m in (57, 60, 64, 69)) / 4
add(music, end - 3.0, lpf(fin, 2000) * np.minimum(1, np.arange(n) / (0.05 * SR)) * np.linspace(1, 0, n) * 0.25)

# SFX: whoosh into each reveal, hit at each reveal
def whoosh(d=0.9):
    n = int(d * SR); x = rng.normal(0, 1, n); t = np.arange(n) / n
    out = np.zeros(n)
    for k in range(0, n, 2048):
        f = 400 + 5000 * (t[k] ** 1.5)
        out[k:k + 2048] = bp(x[k:k + 2048], f * 0.6, min(f * 1.4, 18000))
    return out * np.sin(np.pi * t) ** 2 * 0.5
def hit(big=False):
    n = int(1.2 * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(40 + 90 * np.exp(-t * 20)) / SR) * env_exp(n, 0.35 if big else 0.22)
    s += lpf(rng.normal(0, 1, n), 3000) * env_exp(n, 0.05) * 0.5
    return np.tanh(s * 1.8) * (0.9 if big else 0.6)
def ding():
    n = int(1.0 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)) * env_exp(n, 0.25) * 0.18
for k, s in segs.items():
    if k in ('intro',): continue
    if k != 'r1a':
        add(sfx, s['reveal'] - 0.9, whoosh(), 0.7 if k != 'r1' else 0.3)
    if k.startswith('r') and k != 'r1a':
        add(sfx, s['reveal'], hit(k == 'r1'))
        add(sfx, s['reveal'] + 0.9, ding(), 1.0 if k != 'r1' else 1.5)
add(sfx, segs['r1']['reveal'], crash(), 1.0)
add(sfx, segs['intro']['reveal'] + 0.2, hit(), 0.6)

# voice
def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    # resample 24k -> 44.1k
    idx = np.arange(int(len(x) * SR / sr)) * sr / SR
    return np.interp(idx, np.arange(len(x)), x)
voice = np.zeros(N); duck = np.zeros(N)
for k, s in segs.items():
    v = read_wav(f'voice_{k}.wav'); add(voice, s['voice'], v, 1.0)
    i0 = int((s['voice'] - 0.1) * SR); i1 = int((s['voice'] + len(v) / SR + 0.15) * SR)
    duck[i0:i1] = 1
# smooth ducking
duck = lpf_d = sosfilt(butter(1, 4, fs=SR, output='sos'), duck)
music_gain = 0.55 - 0.40 * np.clip(duck, 0, 1)
mix = music * music_gain + sfx * 0.55 + voice * 2.6
mix = np.tanh(mix * 0.9) / np.tanh(0.9)   # gentle limiter
mix *= 0.89 / np.max(np.abs(mix))
st = np.stack([mix, mix], 1)
with wave.open('mix.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print('ok', N / SR)
def rms(v,a,b): s=v[int(a*SR):int(b*SR)]; return round(20*np.log10(np.sqrt((s**2).mean())+1e-9),1)
mg=music*music_gain
for a,b in [(9,13),(31,36),(83,87)]: print('voice',rms(voice*2.6,a,b),'music',rms(mg,a,b),'sfx',rms(sfx*0.55,a,b))
