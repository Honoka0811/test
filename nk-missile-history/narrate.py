# -*- coding: utf-8 -*-
"""scenes.json の原稿を VOICEVOX(青山龍星)で1文ずつ合成し、
ナレーションの長さからシーン尺・字幕・演出キューの絶対時刻を決めて output/timeline.json に書き出す。
出力: output/narration.wav, output/timeline.json, output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 13 = 青山龍星 ノーマル) / VOICEVOX_SPEED(既定 1.24)
"""
import os, io, re, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.24'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
name = next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == STYLE)
print('VOICEVOX:', name, 'speed', SPEED)

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15     # 抑揚をやや強めて力強く
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 480): idx[-1] + 1440]
    f = min(480, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

cfg = json.load(open(os.path.join(HERE, 'scenes.json'), encoding='utf-8'))
LEAD, GAP, TAIL = cfg['lead'], cfg['gap'], cfg['tail']
clips, scenes, t = [], [], 0.0
for sc in cfg['scenes']:
    start = t; cur = start + LEAD; lines = []
    for ln in sc['lines']:
        x = tts(ln['say'])
        d = len(x) / SR
        clips.append((cur, x))
        lines.append({'start': round(cur, 3), 'end': round(cur + d, 3), 'show': ln['show']})
        print(f"  {cur:6.2f}s +{d:4.2f}s  {ln['show']}")
        cur += d + GAP
    dur = max(sc['min'], cur - GAP + TAIL - start)
    cues = []
    for c in sc.get('cues', []):
        c = dict(c); c['t'] = round(lines[c.pop('line')]['start'] + c.pop('at'), 3)
        for k in ('from', 'to'):
            if isinstance(c.get(k), str): c[k] = cfg['sites'][c[k]]
        cues.append(c)
    scenes.append({'id': sc['id'], 'start': round(start, 3), 'dur': round(dur, 3), 'lines': lines, 'cues': cues})
    print(f"[{sc['id']}] {start:6.2f}s  dur {dur:5.2f}s")
    t = start + dur

total = round(t, 3)
track = np.zeros(int(total * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(total * SR)]
track = track / (np.max(np.abs(track)) + 1e-9) * 0.89
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

json.dump({'total': total, 'scenes': scenes}, open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 0
    for sc in scenes:
        for ln in sc['lines']:
            i += 1
            f.write(f"{i}\n{ts(ln['start'])} --> {ts(min(ln['end'] + 0.2, total))}\n{re.sub(r'\[\[|\]\]', '', ln['show'])}\n\n")
print('total', total, 's  -> output/narration.wav, timeline.json, subtitles_ja.srt')
