# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX:四国めたん で合成し、
各シーンの開始時刻を決めて timings.js(映像側)/ narration.wav / 字幕SRT を書き出す。
映像・BGM はこの timings.js に合わせて作られるので、原稿を変えたら全工程をやり直す(build.sh)。
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.25      # 話速(ショート向けにやや速め)
LEAD = 0.25       # シーン開始から話し始めるまで
TAIL = 0.35       # 話し終わりから次のシーンまで

# (シーンID, 読み上げ原稿, 字幕表記)
SCRIPT = [
    ('hook',    '北海道の鉄道、昔は今の一・五倍もあったって知ってました？JR北海道、最盛期の路線網です！',
                '北海道の鉄道、昔は今の1.5倍もあったって知ってました？JR北海道、最盛期の路線網です！'),
    ('birth',   '千九百八十七年、国鉄民営化でJR北海道が誕生。路線は、二十一線区、三千百七十六点六キロ！',
                '1987年、国鉄民営化でJR北海道が誕生。路線は21線区・3176.6km！'),
    ('trunk',   '大動脈は、函館本線、室蘭本線、千歳線。根室本線は、道東の根室まで。',
                '大動脈は、函館本線・室蘭本線・千歳線。根室本線は、道東の根室まで。'),
    ('north',   '宗谷本線は最北の稚内へ、石北本線はオホーツクの網走へ。',
                '宗谷本線は最北の稚内へ、石北本線はオホーツクの網走へ。'),
    ('local',   'そして今はなき、名寄本線、天北線、池北線。',
                'そして今はなき、名寄本線・天北線・池北線。'),
    ('local2',  '豪雪地帯の深名線に、標津線。レールは網の目のように広がっていました。',
                '豪雪地帯の深名線に、標津線。レールは網の目のように広がっていました。'),
    ('seikan',  '千九百八十八年には、青函トンネルの海峡線が開業。ついに本州とレールでつながります。',
                '1988年には、青函トンネルの海峡線が開業。ついに本州とレールでつながります。'),
    ('decline', 'でも、ここから縮小へ。千九百八十九年、わずか二か月足らずで四路線がJRから消え、深名線、江差線も廃止。',
                'でも、ここから縮小へ。1989年、わずか2か月足らずで4路線がJRから消え、深名線・江差線も廃止。'),
    ('recent',  'さらに、札沼線、日高本線、根室本線の一部。そして二千二十六年、留萌本線も全線廃止。',
                'さらに、札沼線・日高本線・根室本線の一部。そして2026年、留萌本線も全線廃止。'),
    ('compare', '二十一の線区は十二に。在来線は二千九十一点七キロ。約三分の一が消えたんです。',
                '21の線区は12に。在来線は2091.7km。約3分の1が消えたんです。'),
    ('cta',     'あなたが乗ってみたかった路線は？コメントで教えてください！',
                'あなたが乗ってみたかった路線は？コメントで教えてください！'),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    p = pyopenjtalk.OPEN_JTALK_DICT_DIR
    return p.decode() if isinstance(p, bytes) else p

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
name = next((c.name + '/' + st.name) for c in synth.metas() for st in c.styles if st.id == STYLE)
print('engine: VOICEVOX', name)

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15     # 抑揚を少し強めて惹きつける
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

clips, scenes, t = [], [], 0.0
for sid, text, sub in SCRIPT:
    x = tts(text)
    d = len(x) / SR
    dur = round(LEAD + d + TAIL, 2)
    if sid == 'cta': dur = round(dur + 2.2, 2)   # 最後はクレジット表示の余韻
    scenes.append({'id': sid, 'start': round(t, 2), 'dur': dur, 'speech': [round(t + LEAD, 2), round(t + LEAD + d, 2)], 'sub': sub})
    clips.append((t + LEAD, x))
    print(f'{sid:8s} start={t:5.2f} speech={d:4.1f}s dur={dur:4.1f}')
    t += dur
TOTAL = round(t, 2)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.89
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timings.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成(シーン開始時刻とナレーション区間)\n')
    f.write('window.TIMINGS=' + json.dumps({'total': TOTAL, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')

def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, s in enumerate(scenes, 1):
        f.write(f"{i}\n{ts(s['speech'][0])} --> {ts(min(s['speech'][1] + 0.3, TOTAL))}\n{s['sub']}\n\n")
print('total', TOTAL, 's')
