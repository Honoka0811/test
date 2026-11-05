"""BGM (魔王魂 ネオロック73) + 効果音ラボ SE + VOICEVOX narration mix."""
import json, subprocess, wave, numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
SRC = '/tmp/claude-0/-home-user-test/6d1dd308-8d3d-5d9e-bb71-763cdc5e0fc0/scratchpad/sfxsrc/'
TL = json.load(open('timeline.json'))
segs = {s['key']: s for s in TL['segs']}
TOTAL = TL['total']
N = int(SR * (TOTAL + 0.3))

def load(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)

def onset(x, thr_db=-30):
    a = np.abs(x).max(1); thr = a.max() * 10 ** (thr_db / 20)
    return int(np.argmax(a > thr))

def add(buf, t, sig, gain=1.0, align=True):
    if align: sig = sig[onset(sig):]
    i = int(round(t * SR))
    if i < 0: sig = sig[-i:]; i = 0
    j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * gain

def fade(sig, fin=0.0, fout=0.0):
    sig = sig.copy(); n = len(sig)
    if fin: k = min(n, int(fin * SR)); sig[:k] *= np.linspace(0, 1, k)[:, None]
    if fout: k = min(n, int(fout * SR)); sig[n - k:] *= np.linspace(1, 0, k)[:, None]
    return sig

SE = {k: load(SRC + 'se/' + f) for k, f in {
    'don': 'drum-japanese2.mp3', 'swish': 'katana-gesture2.mp3', 'jajan': 'jajean1.mp3',
    'roll': 'drum-roll1.mp3', 'rollend': 'roll-finish1.mp3', 'cracker': 'cracker1.mp3',
    'cheer': 'people-performance-cheer1.mp3', 'roulette': 'electronic-roulette-wheel1.mp3',
    'kira': 'kira1.mp3'}.items()}
# normalise every SE to the same peak so gains below are comparable
for k in SE: SE[k] /= np.abs(SE[k]).max() + 1e-9

music = load(SRC + 'bgm/neorock73.mp3')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0)))
sfx = np.zeros((N, 2)); voice = np.zeros((N, 2))

# --- SE placement ---
add(sfx, 0.25, SE['jajan'], 0.55)
for k, s in segs.items():
    if k in ('intro',): continue
    if k not in ('r1a',):
        add(sfx, s['start'] + 0.1, SE['swish'], 0.45)          # camera move
    if k.startswith('r') and k not in ('r1a', 'r1'):
        add(sfx, s['reveal'], SE['don'], 0.75)                   # 和太鼓ドドン on the beat
        rl = fade(SE['roulette'][:int(0.85 * SR)], 0.02, 0.15)
        add(sfx, s['reveal'] + 0.25, rl, 0.12, align=False)      # count-up ticks
# #1: drumroll -> cymbal + cracker + cheer
r1a, r1 = segs['r1a'], segs['r1']
roll_len = r1['reveal'] - (r1a['reveal'] + 0.2)
roll = SE['roll'][onset(SE['roll']):]
roll = roll[len(roll) - int(roll_len * SR):] if len(roll) > roll_len * SR else roll   # keep the crescendo end
add(sfx, r1['reveal'] - len(roll) / SR, fade(roll, 0.6, 0.03), 0.6, align=False)
add(sfx, r1['reveal'], SE['rollend'], 0.7)
add(sfx, r1['reveal'], SE['don'], 0.8)
add(sfx, r1['reveal'] + 0.08, SE['cracker'], 0.6)
add(sfx, r1['reveal'] + 0.25, fade(SE['cheer'], 0.05, 1.2), 0.32)
add(sfx, segs['outro']['reveal'], SE['kira'], 0.4)

# --- narration ---
def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    idx = np.arange(int(len(x) * SR / sr)) * sr / SR
    y = np.interp(idx, np.arange(len(x)), x)
    return np.stack([y, y], 1)
duck = np.zeros(N)
for k, s in segs.items():
    v = read_wav(f'voice_{k}.wav'); add(voice, s['voice'], v, 1.0, align=False)
    i0 = int((s['voice'] - 0.12) * SR); i1 = int((s['voice'] + len(v) / SR + 0.1) * SR)
    duck[i0:i1] = 1
sm = butter(1, 5, fs=SR, output='sos')
duck = np.clip(sosfilt(sm, duck), 0, 1)

# --- music level automation ---
g = 0.55 - 0.37 * duck                         # ~-10 dB under the voice
t = np.arange(N) / SR
# drop the band out for the drumroll, slam back on the #1 reveal
roll_zone = (t >= r1a['reveal'] - 0.2) & (t < r1['reveal'])
g = np.where(roll_zone, np.minimum(g, 0.06), g)
g = sosfilt(butter(1, 8, fs=SR, output='sos'), g)
g[t >= r1['reveal']] = np.maximum(g[t >= r1['reveal']], 0.0)
# fade out at the end
fo = (t > TOTAL - 2.8)
g[fo] *= np.clip((TOTAL - t[fo]) / 2.8, 0, 1)
mix = music * g[:, None] + sfx * 0.9 + voice * 2.6
pk = np.abs(mix).max(); mix = np.tanh(mix / pk * 1.4) / np.tanh(1.4) * 0.9

with wave.open('mix.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

def rms(v, a, b):
    s = v[int(a * SR):int(b * SR)]; return round(20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9), 1)
mg = music * g[:, None]
for a, b in [(9, 13), (31, 35), (81, 85)]:
    print('voice', rms(voice * 2.6, a, b), 'music', rms(mg, a, b))
print('roll zone music', rms(mg, r1a['reveal'], r1['reveal'] - 0.1), 'sfx', rms(sfx, r1a['reveal'] + 1, r1['reveal'] - 0.1))
