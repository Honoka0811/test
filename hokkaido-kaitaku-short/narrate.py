# -*- coding: utf-8 -*-
"""lines.json の原稿を VOICEVOX(四国めたん ノーマル, style 2)で合成し、
audio/narration.wav・timeline.js(映像側が読むタイミング表)・out/subtitles_ja.srt を書き出す。
事前に VOICEVOX ENGINE を起動しておく:
  docker run -d -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
"""
import json, os, wave, io, urllib.request, urllib.parse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.environ.get('VOICEVOX_URL', 'http://127.0.0.1:50021')
SPEAKER = 2          # 四国めたん(ノーマル)
SPEED = 1.18
SR = 48000
LEAD, GAP_LINE, GAP_SCENE, TAIL = 0.35, 0.14, 0.42, 2.0

def post(path, params, body=None):
    req = urllib.request.Request(B + path + '?' + urllib.parse.urlencode(params),
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    return urllib.request.urlopen(req).read()

def synth(line):
    aq = json.loads(post('/audio_query', {'text': line['read'], 'speaker': SPEAKER}))
    if line.get('kana'):   # 固有名詞の読み・アクセントを AquesTalk 風記法で直接指定
        aq['accent_phrases'] = json.loads(post('/accent_phrases', {'text': line['kana'], 'speaker': SPEAKER, 'is_kana': 'true'}))
    aq.update(speedScale=SPEED, intonationScale=1.15, pauseLengthScale=0.8,
              prePhonemeLength=0.05, postPhonemeLength=0.05, outputSamplingRate=SR, outputStereo=False)
    with wave.open(io.BytesIO(post('/synthesis', {'speaker': SPEAKER}, aq))) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = 300; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

lines = json.load(open(os.path.join(HERE, 'lines.json'), encoding='utf-8'))
t = LEAD; clips = []; cues = []; prev = None
for L in lines:
    x = synth(L)
    if prev is not None:
        t += GAP_SCENE if L['scene'] != prev else GAP_LINE
    prev = L['scene']
    a, b = t, t + len(x) / SR
    clips.append((a, x)); cues.append(dict(id=L['id'], scene=L['scene'], start=round(a, 3), end=round(b, 3), text=L['text'], cap=L['cap']))
    print(f"{a:6.2f}-{b:6.2f}  {L['id']:7s} {L['text']}")
    t = b
TOTAL = round(t + TAIL, 2)
track = np.zeros(int(TOTAL * SR), dtype=np.float32)
for a, x in clips:
    s = int(a * SR); track[s:s + len(x)] += x
track = track / np.max(np.abs(track)) * 0.85
os.makedirs(os.path.join(HERE, 'audio'), exist_ok=True); os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
with wave.open(os.path.join(HERE, 'audio', 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((track * 32767).astype(np.int16).tobytes())
with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps(dict(total=TOTAL, cues=cues), ensure_ascii=False, indent=1) + ';\n')
def ts(t):
    ms = int(round(t * 1000)); return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
with open(os.path.join(HERE, 'out', 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        nxt = cues[i]['start'] if i < len(cues) else TOTAL
        f.write(f"{i}\n{ts(c['start'])} --> {ts(min(c['end'] + 0.25, nxt))}\n{c['text']}\n\n")
print('total', TOTAL)
