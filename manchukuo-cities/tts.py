# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:青山龍星)をシーンごとに合成し、その長さからシーンの尺を決める。
出力:
  output/narration.wav  ナレーション(48kHz mono)
  output/subtitles_ja.srt  字幕
  timing.js  render.html が読むシーン尺・字幕キュー・効果音タイミング
環境変数は pacific-war-analysis/narrate.py と同じ(VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE)
"""
import os, io, re, glob, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = 1.28      # 話速(ショート向けにややテンポ良く)
LEAD = 0.45       # シーン開始からナレーション開始まで
TAIL = 0.55       # ナレーション終了から次のシーンまで

# id, 読み上げ原稿(読みを確実にするため一部かな書き), 字幕(表示用), 最低尺, 追加の余白
SCENES = [
    ('hook', 'わずか十三年で消えた国、満洲国。その主要都市を、人口ランキングで一気に紹介します。',
     'わずか13年で消えた国、満洲国。その主要都市を、人口ランキングで一気に紹介します。', 6.5, 0.3),
    ('overview', '千九百三十二年、中国東北部に建国された満洲国。面積は日本のおよそ三倍、人口は約四千三百万人。主な都市の多くは、鉄道に沿って発展しました。',
     '1932年、中国東北部に建国された満洲国。面積は日本のおよそ3倍、人口は約4300万人。主な都市の多くは、鉄道に沿って発展しました。', 0, 0.4),
    ('r5', '第五位、ぶじゅん。人口およそ二十七万人。巨大な露天掘りで知られる、東洋一の炭鉱の町です。',
     '第5位、撫順。人口およそ27万人。巨大な露天掘りで知られる、東洋一の炭鉱の町です。', 0, 0.3),
    ('r4', '第四位、あんとう。人口およそ三十一万人。オウリョッコウを挟んで朝鮮と向き合う、国境の玄関口です。',
     '第4位、安東。人口およそ31万人。鴨緑江を挟んで朝鮮と向き合う、国境の玄関口です。', 0, 0.3),
    ('r3', '第三位は首都、しんきょう。人口およそ四十九万人。そのうち日本人は約十三万人。実に、四人に一人が日本人でした。',
     '第3位は首都、新京。人口およそ49万人。そのうち日本人は約13万人。実に、4人に1人が日本人でした。', 0, 0.3),
    ('r2', '第二位、ハルビン。人口およそ五十六万人。ロシアが築いた鉄道の町で、東洋のモスクワと呼ばれた国際都市です。日本人は一割に届きませんでした。',
     '第2位、哈爾浜(ハルビン)。人口およそ56万人。ロシアが築いた鉄道の町で、「東洋のモスクワ」と呼ばれた国際都市です。日本人は1割に届きませんでした。', 0, 0.3),
    ('r1', 'そして第一位は、ほうてん。人口は百万人を突破。満洲事変の発火点となった、満洲最大の商工業都市です。日本人も最多の、約十七万人が暮らしました。',
     'そして第1位は、奉天。人口は100万人を突破。満洲事変の発火点となった、満洲最大の商工業都市です。日本人も最多の、約17万人が暮らしました。', 0, 0.6),
    ('bonus', '番外編、だいれん。人口は約六十八万人。ですが実は、満洲国ではなく、日本の租借地、関東州の都市でした。',
     '番外編、大連。人口は約68万人。ですが実は、満洲国ではなく、日本の租借地「関東州」の都市でした。', 0, 0.4),
    ('rail', 'これらの都市を結んだのが鉄道です。だいれんから新京へ延びる満鉄本線。ハルビンを中心に、ロシアが敷いたティーじ型の、とうしん鉄道。そして朝鮮や日本海へ向かう路線が、都市を生み、育てました。',
     'これらの都市を結んだのが鉄道です。大連から新京へ延びる満鉄本線。ハルビンを中心に、ロシアが敷いたT字型の東清鉄道。そして朝鮮や日本海へ向かう路線が、都市を生み、育てました。', 0, 0.6),
    ('asia', '千九百三十四年には、特急あじあ号が登場。だいれんから新京まで、約七百キロを、わずか八時間半で結びました。',
     '1934年には、特急「あじあ」号が登場。大連から新京まで、約700kmを、わずか8時間半で結びました。', 0, 0.4),
    ('end', '千九百四十五年八月、ソ連軍の侵攻で、満洲国は崩壊。その歴史は、わずか十三年五か月でした。あなたが一番気になった都市は、どこですか?',
     '1945年8月、ソ連軍の侵攻で、満洲国は崩壊。その歴史は、わずか13年5か月でした。あなたが一番気になった都市は、どこですか?', 0, 2.6),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    for c in ['/home/user/vv/open_jtalk_dic_utf_8-1.11']:
        if os.path.isdir(c): return c
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    glob.glob('/home/user/vv/ort/*/lib/libvoicevox_onnxruntime.so')[0] if glob.glob('/home/user/vv/ort/*/lib/libvoicevox_onnxruntime.so') else 'libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = 600; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

def split_sub(text):
    """字幕を「。」「?」で区切り、長いものは「、」でさらに分ける(1行 ~22字目安)"""
    parts = [p for p in re.split(r'(?<=[。?])', text) if p]
    out = []
    for p in parts:
        if len(p) <= 24:
            out.append(p); continue
        buf = ''
        for c in re.split(r'(?<=、)', p):
            if buf and len(buf) + len(c) > 24:
                out.append(buf); buf = ''
            buf += c
        if buf: out.append(buf)
    return [o.rstrip('。') for o in out]

clips, scenes, cues = [], [], []
t = 0.0
for sid, read, sub, min_d, extra in SCENES:
    x = tts(read)
    sec = len(x) / SR
    d = max(min_d, LEAD + sec + TAIL + extra)
    scenes.append({'id': sid, 's': round(t, 3), 'd': round(d, 3), 'speech': round(sec, 3)})
    clips.append((t + LEAD, x))
    # 字幕キュー: 文字数に比例して発話区間を分配
    chunks = split_sub(sub)
    total_chars = sum(len(c) for c in chunks)
    a = t + LEAD
    for c in chunks:
        dur = sec * len(c) / total_chars
        cues.append({'s': round(a, 3), 'e': round(a + dur, 3), 't': c})
        a += dur
    print(f'{sid:8s} start={t:6.2f}  speech={sec:5.2f}s  scene={d:5.2f}s')
    t += d
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

def ts(v):
    h, m, s = int(v // 3600), int(v % 3600 // 60), v % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{ts(c['s'])} --> {ts(c['e'])}\n{c['t']}\n\n")

with open(os.path.join(HERE, 'timing.js'), 'w', encoding='utf-8') as f:
    f.write('// 自動生成: python3 tts.py\n')
    f.write('window.TIMING = ' + json.dumps({'total': TOTAL, 'scenes': scenes, 'cues': cues}, ensure_ascii=False, indent=1) + ';\n')
print(f'total {TOTAL:.2f}s  -> timing.js, output/narration.wav, output/subtitles_ja.srt')
