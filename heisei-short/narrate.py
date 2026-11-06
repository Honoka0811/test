# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、セリフの長さからシーンのタイムラインを決める。
出力: output/narration.wav, output/subtitles_ja.srt, timeline.js(render.html が読む)
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000

# id, 読み上げ原稿, 字幕(表示用), シーン前の間(秒), 読み上げ後の余白(秒), 話速, 音高, 抑揚
SCENES = [
    ('hook',  'ねえ、平成を生きた人なら、ぜんぶ分かるはず。あなたは、何個わかる?',
              '平成を生きた人なら\n全部わかるはず\nあなたは何個わかる?', 0.15, 0.35, 1.18, 0.02, 1.35),
    ('cd',    'CDシングルは、細長い、八センチ。',
              'CDシングルは\n細長い8センチ', 0.15, 0.55, 1.12, 0.0, 1.3),
    ('pager', 'ポケベルは数字で会話。ゼロハチヨンゼロで、おはよう。',
              'ポケベルは数字で会話\n0840で「おはよう」', 0.1, 0.55, 1.15, 0.0, 1.3),
    ('puri',  'プリクラは、プリ帳に貼って友だちと交換。',
              'プリクラはプリ帳に貼って\n友だちと交換', 0.1, 0.5, 1.15, 0.0, 1.3),
    ('socks', '女子高生の足元は、ルーズソックス。',
              '女子高生の足元は\nルーズソックス', 0.1, 0.5, 1.15, 0.0, 1.3),
    ('nostra','千九百九十九年、しちの月。世界は、滅亡',
              '1999年7の月\n世界は滅亡…', 0.15, 0.25, 1.05, -0.02, 1.4),
    ('safe',  'しなかった。',
              'しなかった。', 0.35, 0.45, 1.0, 0.03, 1.5),
    ('bill',  '二千年には、二千円札が登場。最近、見た?',
              '2000年には二千円札が登場\n最近見た?', 0.1, 0.5, 1.15, 0.0, 1.35),
    ('melody','ガラケーの着メロは、十六和音で大興奮。',
              'ガラケーの着メロは\n16和音で大興奮', 0.1, 0.5, 1.15, 0.0, 1.3),
    ('ir',    'アドレス交換は、赤外線で、ピッ。',
              'アドレス交換は\n赤外線で「ピッ」', 0.1, 0.55, 1.15, 0.0, 1.35),
    ('end',   'さあ、何個わかった? 全部わかったら、平成マスター。コメントで教えてね!',
              'さあ何個わかった?\n全部わかったら平成マスター\nコメントで教えてね!', 0.2, 1.3, 1.15, 0.02, 1.4),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text, speed, pitch, inton):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = speed; q.pitch_scale = pitch; q.intonation_scale = inton
    q.pre_phoneme_length = 0.02; q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 480): idx[-1] + 1440]
    f = min(480, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, timeline, t = [], [], 0.0
for sid, text, sub, pre, post, speed, pitch, inton in SCENES:
    x = tts(text, speed, pitch, inton)
    d = len(x) / SR
    start = t
    vstart = start + pre
    t = vstart + d + post
    clips.append((vstart, x))
    timeline.append(dict(id=sid, start=round(start, 3), end=round(t, 3), vstart=round(vstart, 3),
                         vend=round(vstart + d, 3), sub=sub))
    print(f'{sid:7s} {start:6.2f}s  voice {d:4.2f}s  {text}')
TOTAL = round(t, 2)
print('total', TOTAL)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) + 1e-9) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成\nwindow.TIMELINE = ' + json.dumps(timeline, ensure_ascii=False, indent=1) +
            ';\nwindow.DURATION = ' + str(TOTAL) + ';\n')

def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(c['vstart'])} --> {ts(min(c['vend'] + 0.3, TOTAL))}\n{c['sub']}\n\n")
print('wrote narration.wav, timeline.js, subtitles_ja.srt')
