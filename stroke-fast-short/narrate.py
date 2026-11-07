# -*- coding: utf-8 -*-
"""VOICEVOX(四国めたん)で各行を合成し、タイムライン(timeline.json)・ナレーション音声(narration.wav)・字幕(SRT)を出力する。
使い方: python3 narrate.py
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np
from script import SCENES, GAP, FPS, STYLE, SPEED

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', '/home/user/vv/dict/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
style = int(os.environ.get('VOICEVOX_STYLE', STYLE))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == style))

def tts(text):
    q = synth.create_audio_query(text, style)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.03
    q.post_phoneme_length = 0.05
    wav = synth.synthesis(q, style)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.003)[0]
    x = x[max(0, idx[0] - 480): idx[-1] + 1440]
    f = 240
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

chunks, timeline, t = [], [], 0.0
for sc in SCENES:
    start = t
    t += sc['pre']
    lines = []
    for i, (say, show) in enumerate(sc['lines']):
        x = tts(say)
        d = len(x) / SR
        chunks.append((t, x))
        lines.append(dict(text=show, say=say, start=round(t, 3), end=round(t + d, 3)))
        t += d + (GAP if i < len(sc['lines']) - 1 else 0)
    t += sc['post']
    timeline.append(dict(id=sc['id'], start=round(start, 3), end=round(t, 3), lines=lines))
    print(f"{sc['id']:7s} {start:6.2f} -> {t:6.2f}  ({t - start:4.1f}s)")

# 全体の長さはフレーム単位に切り上げ
DURATION = np.ceil(t * FPS) / FPS
track = np.zeros(int(DURATION * SR), dtype=np.float32)
for s, x in chunks:
    i = int(s * SR); track[i:i + len(x)] += x
track = track / (np.max(np.abs(track)) or 1) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

json.dump(dict(fps=FPS, duration=DURATION, scenes=timeline), open(os.path.join(OUT, 'timeline.json'), 'w'),
          ensure_ascii=False, indent=1)

def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 0
    for sc in timeline:
        for ln in sc['lines']:
            n += 1
            f.write(f"{n}\n{ts(ln['start'])} --> {ts(min(ln['end'] + 0.25, DURATION))}\n{ln['say']}\n\n")
with open(os.path.join(HERE, 'narration_script.txt'), 'w', encoding='utf-8') as f:
    f.write('脳卒中の見分け方 FAST — ナレーション原稿(VOICEVOX:四国めたん)\n\n')
    for sc in timeline:
        f.write(f"[{sc['id']}] {sc['start']:.1f}s–{sc['end']:.1f}s\n")
        for ln in sc['lines']:
            f.write(f"  {ln['say']}\n")
        f.write('\n')
print(f'duration {DURATION:.2f}s  wrote output/narration.wav, output/timeline.json, output/subtitles_ja.srt')
