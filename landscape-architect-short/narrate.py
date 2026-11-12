# -*- coding: utf-8 -*-
"""VOICEVOX(四国めたん ノーマル, style 2)でナレーションを合成し、
output/narration.wav・output/subtitles_ja.srt・timings.js(映像側が読むタイミング表)を書き出す。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE / VOICEVOX_SPEED
"""
import os, io, glob, json, wave
import numpy as np
from script import SCENES, KANA_FIXES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.25'))
LEAD, GAP, TAIL = 0.45, 0.22, 0.5   # シーン頭の間 / 文間 / シーン末の間(秒)
END_HOLD = 2.2                      # 最後のクレジット表示用の余韻

def dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    pyopenjtalk.g2p('あ')  # 辞書が無ければここで取得される
    return glob.glob(os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic*'))[0]

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT') or
    glob.glob('/home/user/vv/ort/*/lib/libvoicevox_onnxruntime.so')[0])
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    kana = q.kana
    for a, b in KANA_FIXES:
        kana = kana.replace(a, b)
    if kana != q.kana:
        q = synth.create_audio_query_from_kana(kana, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.05
    print('   ', q.kana)
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = 300
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

t = 0.0
chunks, scenes = [], []
for sid, lines in SCENES:
    s0 = t; t += LEAD; ls = []
    for i, (sub, read) in enumerate(lines):
        x = tts(read)
        chunks.append((t, x))
        ls.append({'start': round(t, 3), 'end': round(t + len(x) / SR, 3), 'text': sub})
        t += len(x) / SR + (GAP if i < len(lines) - 1 else 0)
    t += TAIL
    scenes.append({'id': sid, 'start': round(s0, 3), 'dur': round(t - s0, 3), 'lines': ls})
    print(f'{sid:8s} {s0:6.2f}s  dur {t - s0:5.2f}s')
scenes[-1]['dur'] = round(scenes[-1]['dur'] + END_HOLD, 3)
total = round(t + END_HOLD, 3)

track = np.zeros(int(total * SR), dtype=np.float32)
for st, x in chunks:
    s = int(st * SR); track[s:s + len(x)] += x
track *= 0.85 / np.max(np.abs(track))
os.makedirs(OUT, exist_ok=True)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

def ts(v):
    ms = int(round(v * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 0
    for sc in scenes:
        for l in sc['lines']:
            n += 1
            f.write(f"{n}\n{ts(l['start'])} --> {ts(l['end'] + 0.2)}\n{l['text']}\n\n")
with open(os.path.join(HERE, 'timings.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が生成。手で編集しない\nwindow.TIMINGS = ' +
            json.dumps({'total': total, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')
print('total', total, 's')
