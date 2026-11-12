# -*- coding: utf-8 -*-
"""content.json の原稿を VOICEVOX(四国めたん)で合成し、
output/narration.wav・output/bgm.wav・output/mix.wav・timeline.js・output/subtitles_ja.srt を書き出す。
映像(render.html)は timeline.js の時刻に合わせて描画される。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)"""
import os, io, json, glob, wave
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.15
LEAD, GAP, TAIL, END_HOLD = 0.35, 0.22, 0.55, 2.2

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synthz = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', '/home/user/vv/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synthz.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + s.name for c in synthz.metas() for s in c.styles if s.id == STYLE))

def say(text):
    q = (synthz.create_audio_query_from_kana(text[5:], STYLE) if text.startswith('kana:')
         else synthz.create_audio_query(text, STYLE))   # 'kana:' で始まる原稿は読みを直接指定
    q.speed_scale = SPEED; q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.05
    print('   ', q.kana)
    with wave.open(io.BytesIO(synthz.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = 400; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

C = json.load(open(os.path.join(HERE, 'content.json'), encoding='utf-8'))
items = [(C['intro']['say'], C['intro']['sub'])]
items += [(j['say'], [f"{i + 1}. {j['name']}", ''.join(j['tag']) ]) for i, j in enumerate(C['jobs'])]
items += [(C['outro']['say'], C['outro']['sub'])]

clips, scenes, cues, t = [], [], [], 0.0
for si, (says, subs) in enumerate(items):
    start, cur, parts = t, t + LEAD, []
    for text, sub in zip(says, subs):
        x = say(text)
        clips.append((cur, x))
        end = cur + len(x) / SR
        parts.append([round(cur - start, 3), round(end - start, 3)])
        cues.append((cur, end, sub))
        cur = end + GAP
    dur = cur - GAP + TAIL - start + (END_HOLD if si == len(items) - 1 else 0)
    scenes.append({'start': round(start, 3), 'dur': round(dur, 3), 'parts': parts})
    t = start + dur
TOTAL = round(np.ceil(t * 30) / 30, 3)
print(f'total {TOTAL:.2f}s')

voice = np.zeros(int(TOTAL * SR), dtype=np.float32)
for s, x in clips:
    i = int(s * SR); voice[i:i + len(x)] += x
voice *= 0.89 / np.max(np.abs(voice))

def wwav(name, x):
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', name)

os.makedirs(OUT, exist_ok=True)
wwav('narration.wav', voice)
music = bgm_mod.generate(TOTAL)[:len(voice)]
wwav('bgm.wav', music)

# ダッキング: 発話中は BGM を声より約 -17dB、無音時は約 -9dB に
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
v_rms = np.sqrt(np.mean(rms[rms > 0.02] ** 2)); m_rms = np.sqrt(np.mean(music ** 2))
g_speech = v_rms / m_rms * 10 ** (-17 / 20); g_silent = v_rms / m_rms * 10 ** (-9 / 20)
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.repeat(env, hop); env = np.pad(env, (0, len(voice) - len(env)))
sp = np.clip(env / 0.08, 0, 1)
gain = g_silent - (g_silent - g_speech) * sp
k = SR // 10; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = voice + music * gain
wwav('mix.wav', mix / max(1.0, np.max(np.abs(mix)) / 0.95))

with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps({'total': TOTAL, 'scenes': scenes}) + ';\n')
    f.write('window.CONTENT = ' + json.dumps(C, ensure_ascii=False) + ';\n')

def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, s) in enumerate(cues, 1):
        f.write(f'{i}\n{ts(a)} --> {ts(b + 0.15)}\n{s}\n\n')
print('wrote timeline.js, subtitles_ja.srt')
