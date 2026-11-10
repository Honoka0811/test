# -*- coding: utf-8 -*-
"""script.json のナレーションを合成し、各セリフの長さから動画のタイムライン(timeline.json)を決める。
既定は VOICEVOX(四国めたん ノーマル, style 2)。voicevox_core が無い場合は Open JTalk(女性音声)にフォールバック。
出力: output/narration.wav, output/timeline.json(.js), output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2)/ SPEED(既定 1.18)
"""
import os, io, json, glob, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = float(os.environ.get('SPEED', '1.18'))
S = json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    name = 'VOICEVOX'
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        self.label = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', self.label)
    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(self.synth.synthesis(q, self.style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    name = 'OpenJTalk'
    label = 'Open JTalk (mei)'
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback)')
    def __call__(self, text):
        x, sr = self.tts(text, speed=SPEED)
        return x.astype(np.float32) / 32768.0, sr

try:
    engine = VoicevoxEngine()
except Exception as e:
    print('VOICEVOX unavailable:', e)
    engine = OpenJtalkEngine()

def synth(text):
    x, sr = engine(text)
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx): x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

# シーン: (種類, データ, 発話前の間, 発話後の間)
scenes = [('intro', S['intro'], 1.6, 0.5)]
scenes += [('item', it, 0.55, 0.45) for it in S['items']]
scenes += [('outro', S['outro'], 0.5, 1.8)]

clips, timeline, t = [], [], 0.0
for kind, d, pre, post in scenes:
    if kind == 'item' and d['rank'] == 1: pre += 0.6   # 1位の前は少し溜める
    x = synth(d['say'])
    dur = len(x) / SR
    sc = {'kind': kind, 'start': round(t, 3), 'voice': round(t + pre, 3), 'voiceEnd': round(t + pre + dur, 3),
          'end': round(t + pre + dur + post, 3), 'sub': d['sub']}
    if kind == 'item':
        sc.update({k: d[k] for k in ('rank', 'name', 'origin', 'pain', 'icon')})
    timeline.append(sc); clips.append((t + pre, x))
    print(f"{kind:5s} {sc.get('rank', ''):>2}  {t:5.1f}s  voice {dur:4.1f}s")
    t = sc['end']
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for st, x in clips:
    s = int(st * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

credit = f'VOICEVOX:四国めたん' if engine.name == 'VOICEVOX' else engine.label
TLD = {'total': TOTAL, 'title': S['title'], 'credit': credit, 'scenes': timeline}
json.dump(TLD, open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:  # render.html 用
    f.write('window.TL = ' + json.dumps(TLD, ensure_ascii=False) + ';\n')

def ts(x):
    return f'{int(x//3600):02d}:{int(x%3600//60):02d}:{int(x%60):02d},{int(round((x-int(x))*1000))%1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, sc in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(sc['voice'])} --> {ts(min(sc['voiceEnd'] + 0.3, TOTAL))}\n{sc['sub']}\n\n")
print('total', TOTAL, 's  credit:', credit)
