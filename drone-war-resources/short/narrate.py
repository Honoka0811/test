# -*- coding: utf-8 -*-
"""ショート版ナレーション(VOICEVOX: 青山龍星)。60秒以内に収まるよう話速を自動調整する。
出力: output/narration.wav, output/timing.json, output/subtitles_ja.srt
"""
import sys, os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
LIMIT = 59.0                 # ショートの上限(秒)
LEAD, GAP, TAIL = 0.5, 0.3, 0.5
END_DUR = 3.2

SCRIPT = [
    ('title', [('エーアイドローンの消耗戦。勝敗を決めるのは、ドローンの数ではなく、代替の利かない工程です。',
                'AIドローンの消耗戦。勝敗を決めるのは、ドローンの数ではなく、代替の利かない工程です。')]),
    ('semi',  [('半導体。イーユーブイ露光機を作れるのはエーエスエムエル一社。エーアイ用ジーピーユーは、ウェハではなくコワスというパッケージングが足りません。',
                '半導体。EUV露光機を作れるのはASML 1社。AI用GPUは、ウェハではなくCoWoSというパッケージングが足りません。')]),
    ('power', [('電力。大型ガスタービンは受注残が百ギガワット超で、納期は三年以上。大型変圧器は平均百二十八週待ちです。',
                '電力。大型ガスタービンは受注残が100GW超で、納期は3年以上。大型変圧器は平均128週待ちです。')]),
    ('drone', [('ドローン生産。モーターのネオジム磁石は中国が九十四パーセント。炸薬のアールディーエックスは、米国内でも完全には作れません。',
                'ドローン生産。モーターのネオジム磁石は中国が94%。炸薬のRDXは、米国内でも完全には作れません。')]),
    ('space', [('宇宙インフラ。スターリンク・ミニは約一キログラム、二十五ワット。エフピーブイには載らず、しかも米国の一企業が止められます。',
                '宇宙インフラ。Starlink Miniは約1kg、25W。FPVには載らず、しかも米国の一企業が止められます。')]),
    ('data',  [('データと人材。前線の映像を数週間でモデルに反映できるか。これは物理資源ではなく、制度の問題です。', None)]),
    ('outro', [('急所は陣営ごとに違います。詳しくは本編で。', None)]),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.08
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

engine = VoicevoxEngine()

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def synth(text, speed):
    x, sr = engine(text, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1000): idx[-1] + 1600]
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

def build(speed):
    clips, timing, t = [], {'scenes': []}, 0.0
    for sid, beats in SCRIPT:
        scene = {'id': sid, 'start': round(t, 3), 'beats': []}
        bt = t + (0.9 if sid == 'title' else LEAD)
        for tts, sub in beats:
            x = synth(tts, speed); sec = len(x) / SR
            clips.append((bt, x))
            scene['beats'].append({'start': round(bt, 3), 'end': round(bt + sec, 3), 'sub': sub or tts, 'reveal': [0]})
            bt += sec + GAP
        t = bt - GAP + TAIL
        scene['dur'] = round(t - scene['start'], 3)
        timing['scenes'].append(scene)
    timing['scenes'].append({'id': 'end', 'start': round(t, 3), 'dur': END_DUR, 'beats': []})
    t += END_DUR
    timing['total'] = round(t, 3)
    return clips, timing

speed = float(os.environ.get('SPEED', '1.12'))
for _ in range(5):
    clips, timing = build(speed)
    print(f'speed {speed:.2f} → total {timing["total"]:.1f}s')
    if timing['total'] <= LIMIT: break
    speed = min(round(speed * timing['total'] / LIMIT * 1.01, 3), 1.35)
TOTAL = timing['total']
for sc in timing['scenes']:
    for b in sc['beats']: print(f"{b['start']:5.1f}s {b['end']-b['start']:4.1f}s [{sc['id']}] {b['sub'][:20]}…")

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
os.makedirs(OUT, exist_ok=True)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
json.dump(timing, open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timing['scenes']:
        for b in sc['beats']:
            f.write(f"{i}\n{_ts(b['start'])} --> {_ts(min(b['end'] + 0.3, TOTAL))}\n{b['sub']}\n\n"); i += 1
print('wrote', OUT, f'total {TOTAL:.1f}s')
