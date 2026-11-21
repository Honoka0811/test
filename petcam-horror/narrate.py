# -*- coding: utf-8 -*-
"""ナレーションを VOICEVOX で合成し、その長さからシーンの尺を決めて
output/timeline.js(render.html が読む)・output/narration.wav・output/subtitles_ja.srt を書き出す。
使い方: python3 narrate.py
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT(pacific-war-analysis/narrate.py と同じ)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000

METAN, SAYO = 2, 46      # 飼い主 = 四国めたん ノーマル / 友達 = 小夜/SAYO ノーマル

# シーンごとのセリフ: (シーンID, [(原稿, 字幕, 話者, 話速, 前の間), ...], シーン末の間)
#   話者: 'me' = 飼い主(四国めたん) / 'friend' = 友達(小夜)
SCRIPT = [
    ('day1',    [('留守中のペットカメラ。うちのコタが、誰もいない所に、ずっと尻尾を振ってる。',
                  '留守中のペットカメラ\nうちのコタが\n誰もいない所に尻尾を振ってる', 'me', 1.1, 0.2)], 0.5),
    ('day3',    [('次の日も、その次の日も。同じ場所で、お手までしてる。',
                  '次の日も、その次の日も\n同じ場所で\nお手までしてる', 'me', 1.1, 0.2)], 0.6),
    ('grandma', [('そこは、去年亡くなったおばあちゃんが、いつも座ってた場所。',
                  'そこは去年亡くなった\nおばあちゃんが\nいつも座ってた場所', 'me', 1.05, 0.2),
                 ('会いに来てくれてるのかなって、ちょっと泣いた。',
                  '会いに来てくれてるのかなって\nちょっと泣いた', 'me', 1.05, 0.3)], 0.7),
    ('friend',  [('友達に録画を見せたら、急に真顔になった。',
                  '友達に録画を見せたら\n急に真顔になった', 'me', 1.1, 0.2),
                 ('ねえ……テレビ、見て。',
                  '「ねえ……テレビ、見て」', 'friend', 0.9, 0.5)], 0.4),
    ('zoom',    [], 3.6),
    ('reveal',  [('テレビの画面に、知らない男が映ってた。',
                  'テレビの画面に\n知らない男が映ってた', 'me', 1.0, 0.3),
                 ('手には、コタのおやつ。',
                  '手には、コタのおやつ', 'me', 1.0, 0.4),
                 ('毎日来てたのは、コタを、吠えなくするためだった。',
                  '毎日来てたのは\nコタを吠えなくするためだった', 'me', 1.0, 0.5)], 1.0),
    ('tonight', [('今夜、リビングで物音がした。',
                  '今夜、リビングで\n物音がした', 'me', 1.0, 0.9),
                 ('コタは、吠えなかった。',
                  'コタは、吠えなかった', 'me', 0.95, 0.5)], 6.2),
    ('end',     [], 2.8),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return pyopenjtalk.OPEN_JTALK_DICT_DIR.decode()

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)

def tts(text, who, speed):
    style = METAN if who == 'me' else SAYO
    q = synth.create_audio_query(text, style)
    q.speed_scale = speed
    q.pitch_scale = -0.02 if who == 'me' else -0.04
    q.intonation_scale = 0.9 if who == 'me' else 0.7
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    x = x / (np.max(np.abs(x)) or 1)
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, scenes, cues = [], [], []
t = 0.0
for sid, lines, post in SCRIPT:
    start = t
    for text, sub, who, speed, pre in lines:
        x = tts(text, who, speed)
        a = t + pre
        b = a + len(x) / SR
        clips.append((a, x))
        cues.append({'a': round(a, 3), 'b': round(b + 0.2, 3), 'text': sub, 'kind': who})
        t = b
    t += post
    scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3)})
    print(f'{sid:8s} {start:6.2f} → {t:6.2f}')
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for a, x in clips:
    s = int(a * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)] * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

tl = {'total': TOTAL, 'scenes': scenes, 'cues': cues}
with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(tl, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')

def _ts(s):
    return f'{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(round((s % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{_ts(c['a'])} --> {_ts(c['b'])}\n{c['text']}\n\n")
print('total', TOTAL, 's  → output/narration.wav, timeline.js, subtitles_ja.srt')
