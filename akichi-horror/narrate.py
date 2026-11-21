# -*- coding: utf-8 -*-
"""ナレーションを VOICEVOX(青山龍星)で合成し、その長さからシーンの尺を決めて
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

SHITTORI, SASAYAKI = 84, 86   # 青山龍星 しっとり / 囁き

# (シーンID, 読み上げ原稿, 字幕, スタイル, 話速, 前の間, 後の間)
SCRIPT = [
    ('title',    None, None, None, 0, 0, 3.2),
    ('lot',      'うちの近所に、ずっと空き地がある。',
                 'うちの近所に、\nずっと空き地がある。', SHITTORI, 1.0, 0.5, 0.9),
    ('sign',     '看板には、売地の文字。でも、電話番号だけが、黒く塗りつぶされている。',
                 '看板には「売地」の文字。\nでも電話番号だけが\n黒く塗りつぶされている。', SHITTORI, 1.0, 0.3, 0.9),
    ('ground',   '不思議なことに、草が一本も生えていない。真夏でも。',
                 '不思議なことに\n草が一本も生えていない。\n……真夏でも。', SHITTORI, 1.0, 0.3, 1.0),
    ('clock',    'そして、毎晩、午前二時。',
                 'そして毎晩、午前2時。', SHITTORI, 0.95, 0.4, 0.6),
    ('figure',   '空き地の真ん中に、誰かが立っている。',
                 '空き地の真ん中に\n誰かが立っている。', SHITTORI, 0.95, 0.3, 1.4),
    ('neighbor', '近所の人に、聞いてみた。あの空き地、前は何があったんですか。',
                 '近所の人に聞いてみた。\n「あの空き地、\n前は何があったんですか」', SHITTORI, 1.0, 0.3, 0.4),
    ('answer',   '空き地? そんなもの、どこにあるの?',
                 '「空き地?\nそんなもの、どこにあるの?」', SASAYAKI, 0.95, 0.4, 1.2),
    ('approach', '昨日の夜、ついに近づいてみた。その人影は、私と同じ服を着ていた。',
                 '昨日の夜、ついに近づいてみた。\nその人影は……\n私と同じ服を着ていた。', SHITTORI, 0.95, 0.4, 1.0),
    ('window',   '振り返ると、私の部屋の窓から、誰かが、こっちを見ていた。',
                 '振り返ると、私の部屋の窓から\n誰かが、こっちを見ていた。', SHITTORI, 0.95, 0.4, 0.3),
    ('scare',    None, None, None, 0, 0, 1.3),
    ('end',      '今夜、二時。窓の外は、見ないでください。',
                 '今夜2時。\n窓の外は、見ないでください。', SASAYAKI, 0.9, 1.0, 2.6),
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

def tts(text, style, speed):
    q = synth.create_audio_query(text, style)
    q.speed_scale = speed
    q.pitch_scale = -0.03          # 少し低く
    q.intonation_scale = 0.85      # 抑揚を抑えて淡々と
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
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, scenes, cues = [], [], []
t = 0.0
for sid, text, sub, style, speed, pre, post in SCRIPT:
    start = t
    if text:
        x = tts(text, style, speed)
        a = start + pre
        b = a + len(x) / SR
        clips.append((a, x))
        cues.append({'a': round(a, 3), 'b': round(b + 0.25, 3), 'text': sub})
        t = b + post
    else:
        t = start + post
    scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3)})
    print(f'{sid:9s} {start:6.2f} → {t:6.2f}')
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for a, x in clips:
    s = int(a * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.9
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
