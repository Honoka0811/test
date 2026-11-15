# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その長さから各シーンの尺を決めて
output/narration.wav・timeline.js(render.html が読む)・output/subtitles_ja.srt を書き出す。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
          VOICE_SPEED(既定 1.28)"""
import os, io, wave, glob, json
import numpy as np
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
LEAD, TAIL = 0.30, 0.45          # シーン頭の間 / 発話後の余韻
VV = '/home/user/vv'

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
SPEED = float(os.environ.get('VOICE_SPEED', '1.28'))
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text, speed):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = speed
    q.intonation_scale = 1.15     # 少しだけ抑揚を強めてショート動画向けに
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, timeline, t = [], [], 0.0
for sc in SCENES:
    sp = SPEED * (1.05 if sc['kind'] == 'rank' and sc['rank'] != 1 else 1.0)
    x = tts(sc['read'], sp)
    sec = len(x) / SR
    extra = 0.6 if sc['kind'] == 'outro' else (0.4 if sc.get('rank') == 1 else 0)
    dur = round(LEAD + sec + TAIL + extra, 2)
    clips.append((t + LEAD, x))
    timeline.append({**{k: v for k, v in sc.items() if k != 'read'}, 'start': round(t, 3), 'dur': dur,
                     'vs': round(t + LEAD, 3), 've': round(t + LEAD + sec, 3)})
    print(f'{t:6.2f}s  dur={dur:5.2f}  speech={sec:4.2f}  {sc["sub"][:20]}')
    t += dur
TOTAL = round(t, 2)

track = np.zeros(int(TOTAL * SR) + SR // 10, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// voice.py が生成(手で編集しない)\nwindow.TIMELINE = ' +
            json.dumps({'total': TOTAL, 'scenes': timeline}, ensure_ascii=False, indent=1) + ';\n')

def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, s in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(s['vs'])} --> {ts(min(s['ve'] + 0.3, TOTAL))}\n{s['sub']}\n\n")
print('total', TOTAL, 's')
