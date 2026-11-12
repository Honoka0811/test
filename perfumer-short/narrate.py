# -*- coding: utf-8 -*-
"""script.py の原稿を VOICEVOX(四国めたん ノーマル)で合成し、
output/narration.wav と、シーン・字幕のタイミング output/timeline.json を書き出す。
シーンの長さはナレーションの長さから自動で決まる。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = 1.2        # 話速
GAP = 0.32          # 文と文の間
SCENE_LEAD = 0.45   # シーン開始からナレーションまで
SCENE_TAIL = 0.55   # ナレーション終了からシーン切り替えまで
END_HOLD = 2.6      # 最後のシーンの余韻

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', '/home/user/vv/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == STYLE))

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = 600
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, scenes, t = [], [], 0.0
for si, (key, lines) in enumerate(SCENES):
    start = t
    t += SCENE_LEAD
    subs = []
    for li, (read, disp) in enumerate(lines):
        x = tts(read)
        d = len(x) / SR
        clips.append((t, x))
        subs.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': disp})
        t += d + (GAP if li < len(lines) - 1 else 0)
    t += END_HOLD if si == len(SCENES) - 1 else SCENE_TAIL
    scenes.append({'key': key, 'start': round(start, 3), 'end': round(t, 3), 'subs': subs})
    print(f'{key:10s} {start:5.2f}–{t:5.2f}s ({t - start:4.1f}s)')

TOTAL = round(t, 3)
track = np.zeros(int(TOTAL * SR) + 1, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x[:len(track) - i]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump({'total': TOTAL, 'scenes': scenes}, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:   # render.html が読み込む
    f.write('window.TL = ' + json.dumps({'total': TOTAL, 'scenes': scenes}, ensure_ascii=False) + ';\n')

# 字幕 SRT
def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 1
    for sc in scenes:
        for s in sc['subs']:
            f.write(f"{n}\n{ts(s['start'])} --> {ts(s['end'] + 0.2)}\n{s['text'].replace('|', '')}\n\n"); n += 1
print(f'total {TOTAL:.2f}s  → output/narration.wav, timeline.json, subtitles_ja.srt')
