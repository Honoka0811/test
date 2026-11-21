# -*- coding: utf-8 -*-
"""ナレーションを VOICEVOX(青山龍星)で合成し、その長さからシーンの尺を決めて
output/timeline.js(render.html が読む)・output/narration.wav・output/subtitles_ja.srt を書き出す。
電話の向こうの声(kind='phone')には電話回線風のフィルタをかける。
使い方: python3 narrate.py
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT(pacific-war-analysis/narrate.py と同じ)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000

NORMAL, SASAYAKI, SHITTORI = 13, 86, 84   # 青山龍星 ノーマル / 囁き / しっとり

# (シーンID, 読み上げ原稿, 字幕, スタイル, 話速, 種別, 前の間, 後の間)
#   種別: 'me' = 主人公の独り言 / 'phone' = 電話の向こうの「俺」の声 / 'close' = 耳元の声
SCRIPT = [
    ('sign',    '近所の空き地の看板。電話番号だけ、黒く塗りつぶされてる。',
                '近所の空き地の看板\n電話番号だけ\n塗りつぶされてる', SHITTORI, 1.1, 'me', 0.15, 0.4),
    ('scratch', '気になって、削ってみた。',
                '気になって\n削ってみた', SHITTORI, 1.1, 'me', 0.2, 1.6),
    ('reveal',  'これ……俺の番号だ。',
                'これ……\n俺の番号だ', SHITTORI, 1.0, 'me', 0.3, 1.0),
    ('call',    'かけてみた。',
                'かけてみた', SHITTORI, 1.05, 'me', 0.2, 3.4),
    ('answer',  '出たのは、俺の声だった。',
                '出たのは\n俺の声だった', SHITTORI, 1.0, 'me', 0.6, 0.5),
    ('phone',   'いま、空き地にいるよ。',
                '「いま、空き地にいるよ」', SASAYAKI, 0.9, 'phone', 0.2, 0.8),
    ('sweep',   '空き地の真ん中で、スマホが光ってた。',
                '空き地の真ん中で\nスマホが光ってた', SHITTORI, 1.05, 'me', 0.9, 1.6),
    ('behind',  '振り向いたら、交代な。',
                '「振り向いたら、交代な」', SASAYAKI, 0.85, 'close', 1.4, 1.4),
    ('end',     None, None, None, 0, None, 0, 3.2),
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

def tts(text, style, speed, kind):
    q = synth.create_audio_query(text, style)
    q.speed_scale = speed
    q.pitch_scale = -0.02 if kind == 'me' else -0.05
    q.intonation_scale = 0.9 if kind == 'me' else 0.6
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
    if kind == 'phone':      # 電話回線: 300〜3400Hz に帯域制限 + 軽い歪み
        X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
        X *= (fr > 300) & (fr < 3400); x = np.fft.irfft(X, len(x)).astype(np.float32)
        x = np.tanh(x / (np.max(np.abs(x)) or 1) * 2.5) * 0.8
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, scenes, cues = [], [], []
t = 0.0
for sid, text, sub, style, speed, kind, pre, post in SCRIPT:
    start = t
    if text:
        x = tts(text, style, speed, kind)
        a = start + pre
        b = a + len(x) / SR
        clips.append((a, x, kind))
        cues.append({'a': round(a, 3), 'b': round(b + 0.25, 3), 'text': sub, 'kind': kind})
        t = b + post
    else:
        t = start + post
    scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3)})
    print(f'{sid:8s} {start:6.2f} → {t:6.2f}')
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for a, x, kind in clips:
    s = int(a * SR); track[s:s + len(x)] += x / (np.max(np.abs(x)) or 1) * (0.75 if kind == 'phone' else 1.0)
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
