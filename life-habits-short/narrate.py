# -*- coding: utf-8 -*-
"""台本(script.py)を VOICEVOX:四国めたん で読み上げ、実際の発話長からシーン構成を決める。
出力:
  output/narration.wav  ナレーションのみ(48kHz mono)
  timeline.js           render.html が読むタイムライン(window.TL)
  output/timeline.json  mix.py(BGM/効果音)が読むタイムライン
  output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np
import script as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICE_SPEED', '1.3'))
VV = os.environ.get('VOICEVOX_HOME', os.path.expanduser('~/vv') if os.path.isdir(os.path.expanduser('~/vv')) else '/home/user/vv')


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    d = os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
    if not os.path.isdir(d):
        pyopenjtalk.g2p('あ')  # 初回は辞書を自動ダウンロード
    return d


class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get(
            'VOICEVOX_ORT', f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.s = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.s.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next(c.name + '/' + st.name for c in self.s.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)

    def __call__(self, text, speed=SPEED, intonation=1.18, pitch=0.0):
        q = self.s.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.intonation_scale = intonation
        q.pitch_scale = pitch
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.08
        b = self.s.synthesis(q, self.style)
        with wave.open(io.BytesIO(b)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        # 48kHz へ
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 600): idx[-1] + 1800]
        f = min(400, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x


tts = Voicevox()
clips = []      # (開始秒, 波形)
scenes = []
t = 0.0


def say(read, start, **kw):
    x = tts(read, **kw)
    clips.append((start, x))
    return start + len(x) / SR


def chunk(c, s, e, kind='line'):
    return dict(s=round(s, 3), e=round(e, 3), text=c['text'], hl=c.get('hl', ''), kind=kind)

# ---- フック ----
sc = dict(type='hook', start=0.0, chunks=[])
p = 0.25
for i, c in enumerate(S.HOOK):
    e = say(c['read'], p, intonation=1.25 if i else 1.05)
    sc['chunks'].append(chunk(c, p, e))
    p = e + (0.25 if i == 0 else 0.12)
sc['end'] = round(p + 0.15, 3)
scenes.append(sc)
drop = sc['chunks'][1]['s']
t = sc['end']

# ---- 10位 → 2位、ティーザー、1位 ----
def rank_scene(h, t, first=False):
    sc = dict(type='rank', start=round(t, 3), rank=h['rank'], emoji=h['emoji'], title=h['title'], theme=h['theme'], chunks=[])
    p = t + (0.75 if first else 0.42)
    e = say(h['read_title'], p, intonation=1.35, speed=SPEED * (0.97 if first else 1.0))
    sc['chunks'].append(dict(s=round(p, 3), e=round(e, 3), text=h['title'], hl='', kind='title'))
    p = e + 0.14
    e = say(h['read'], p)
    sc['chunks'].append(chunk(h, p, e, 'reason'))
    sc['end'] = round(e + (0.75 if first else 0.32), 3)
    return sc

for h in S.HABITS:
    sc = rank_scene(h, t); scenes.append(sc); t = sc['end']

sc = dict(type='teaser', start=round(t, 3), chunks=[])
p = t + 0.3
e = say(S.TEASER['read'], p, intonation=1.0, speed=SPEED * 0.92, pitch=-0.02)
sc['chunks'].append(chunk(S.TEASER, p, e))
sc['end'] = round(e + 1.0, 3)   # ドラムロールの溜め
scenes.append(sc); t = sc['end']

sc = rank_scene(S.FIRST, t, first=True); scenes.append(sc); t = sc['end']

sc = dict(type='outro', start=round(t, 3), chunks=[])
p = t + 0.35
for c in S.OUTRO:
    e = say(c['read'], p, intonation=1.25)
    sc['chunks'].append(chunk(c, p, e))
    p = e + 0.2
sc['end'] = round(p + 2.6, 3)
scenes.append(sc)
DURATION = round(sc['end'], 2)

# ---- 書き出し ----
track = np.zeros(int(DURATION * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(DURATION * SR)]
track = track / (np.max(np.abs(track)) + 1e-9) * 0.89
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

tl = dict(title=S.TITLE, duration=DURATION, drop=round(drop, 3), scenes=scenes,
          recap=[dict(rank=h['rank'], emoji=h['emoji'], title=h['title']) for h in [S.FIRST] + S.HABITS[::-1]])
with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成。手で編集しないこと\nwindow.TL = ' + json.dumps(tl, ensure_ascii=False, indent=1) + ';\n')
with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(tl, f, ensure_ascii=False, indent=1)


def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}'

with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 0
    for sc in scenes:
        for c in sc['chunks']:
            n += 1
            txt = (f"第{sc['rank']}位 " + c['text']) if c['kind'] == 'title' else c['text']
            f.write(f"{n}\n{ts(c['s'])} --> {ts(min(c['e'] + 0.25, DURATION))}\n{txt}\n\n")

for sc in scenes:
    print(f"{sc['start']:6.2f}–{sc['end']:6.2f}  {sc['type']:6s} {sc.get('rank', '')!s:>2}  {sc.get('title', sc['chunks'][0]['text'].splitlines()[0])}")
print('duration', DURATION, 's   drop at', round(drop, 2))
