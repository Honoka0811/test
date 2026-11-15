# -*- coding: utf-8 -*-
"""台本(script.py)を VOICEVOX(四国めたん)で合成し、
 - 実際の音声の長さからシーン尺を決めて output/timeline.js(render.html が読む)を書き出す
 - BGM(ナレーション中は自動で音量ダウン)と効果音をミックスして output/mix.wav を書き出す
 - 字幕 output/subtitles_ja.srt を書き出す
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np
from script import SCENES
import bgm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = bgm.SR
SPEED = 1.22

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text, intonation=1.15):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = intonation
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = 400; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

# ---------- タイムライン ----------
GAP = 0.16          # 行間
LEAD = {'title': 0.6, 'intro': 0.5, 'round': 0.75, 'result': 0.5, 'outro': 0.4}
TAIL = {'title': 0.5, 'intro': 0.6, 'round': 1.0, 'result': 0.7, 'outro': 2.0}

clips, timeline, sfx = [], [], []
t = 0.0
for sc in SCENES:
    start = t
    t += LEAD[sc['id']]
    lines = []
    for li, (read, sub) in enumerate(sc['lines']):
        excited = sc['id'] == 'round' and li == len(sc['lines']) - 1
        x = tts(read, 1.35 if excited else 1.15)
        clips.append((t, x))
        lines.append(dict(t0=round(t, 3), t1=round(t + len(x) / SR, 3), sub=sub))
        t += len(x) / SR + GAP
    t += TAIL[sc['id']] - GAP
    meta = {k: v for k, v in sc.items() if k != 'lines'}
    timeline.append(dict(meta, start=round(start, 3), dur=round(t - start, 3), lines=lines))
    # 効果音
    if sc['id'] in ('title', 'round'): sfx.append((start + 0.05, 'impact'))
    if sc['id'] == 'round': sfx.append((lines[-1]['t0'] - 0.05, 'win'))
    if sc['id'] == 'round': sfx.append((lines[1]['t0'], 'pop'))
    if sc['id'] == 'intro': sfx += [(lines[0]['t0'], 'pop'), (lines[1]['t0'], 'pop')]
    if sc['id'] == 'result': sfx.append((start + 0.1, 'draw'))
TOTAL = round(t, 2)
for s in timeline: print(f"{s['start']:5.1f}s +{s['dur']:4.1f}s  {s['id']}")
print('total', TOTAL)

with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps(dict(total=TOTAL, scenes=timeline), ensure_ascii=False, indent=1) + ';\n')

# ---------- ナレーション ----------
n = int(TOTAL * SR)
voice = np.zeros(n, np.float32)
for st, x in clips: bgm.add(voice, st, x)
voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.85
def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
write(os.path.join(OUT, 'narration.wav'), voice)

# ---------- 字幕 ----------
def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 0
    for s in timeline:
        for ln in s['lines']:
            i += 1
            f.write(f"{i}\n{ts(ln['t0'])} --> {ts(min(ln['t1'] + 0.25, TOTAL))}\n{ln['sub']}\n\n")

# ---------- BGM(ダッキング)+ 効果音 ----------
music = bgm.generate(TOTAL)[:n]
hop = SR // 20
rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, n - len(rms) * hop))
gain = 0.36 - (0.36 - 0.15) * np.clip(env / 0.1, 0, 1)
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
fx = np.zeros(n, np.float32)
FX = dict(impact=(bgm.sfx_impact, 0.55), win=(bgm.sfx_win, 0.35), draw=(bgm.sfx_draw, 0.45), pop=(bgm.sfx_pop, 0.25))
for st, kind in sfx:
    fn, g = FX[kind]; bgm.add(fx, st, fn(), g)
write(os.path.join(OUT, 'bgm.wav'), music)
mix = voice + music * gain + fx
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)
write(os.path.join(OUT, 'mix.wav'), mix)
print('wrote narration.wav / bgm.wav / mix.wav / timeline.js / subtitles_ja.srt')
