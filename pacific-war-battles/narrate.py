# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:青山龍星)をシーンごとに合成し、その長さからシーン尺を決める。
出力: output/narration.wav, output/subtitles_ja.srt, timeline.js(render.html が読む)
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 13 = 青山龍星 ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.2       # 全シーン共通の話速
LEAD = 0.55       # シーン開始から読み始めまで
TAIL = 0.65       # 読み終わりから次のシーンまで

# (シーンID, 読み上げ用テキスト, 字幕テキスト, 最低シーン長)
SCRIPT = [
    ('title', '太平洋戦争の激戦。七つの戦いを、時代順にたどります。',
              '太平洋戦争の激戦。7つの戦いを、時代順にたどります。', 5.0),
    ('midway', '千九百四十二年六月、ミッドウェー海戦。にほんは主力空母四隻と、多くの熟練搭乗員を失い、戦局の転換点となりました。',
               '1942年6月、ミッドウェー海戦。日本は主力空母4隻と、多くの熟練搭乗員を失い、戦局の転換点となりました。', 0),
    ('guadalcanal', 'ガダルカナル島の戦い。半年に及ぶ消耗戦で、にほんぐんは約二万人が死亡。その多くが餓死や病死で、ガトウと呼ばれました。',
                    'ガダルカナル島の戦い。半年に及ぶ消耗戦で、日本軍は約2万人が死亡。その多くが餓死や病死で、「餓島」と呼ばれました。', 0),
    ('mariana', '千九百四十四年六月、マリアナおき海戦。空母三隻と、航空機およそ四百機を失い、にほんの空母機動部隊は壊滅しました。',
                '1944年6月、マリアナ沖海戦。空母3隻と、航空機およそ400機を失い、日本の空母機動部隊は壊滅しました。', 0),
    ('saipan', '続くサイパン島の戦いでは、守備隊約三万人がほぼ全滅。民間人も約一万人が犠牲となり、本土はビーにじゅうくの爆撃圏に入りました。',
               '続くサイパン島の戦いでは、守備隊約3万人がほぼ全滅。民間人も約1万人が犠牲となり、本土はB-29の爆撃圏に入りました。', 0),
    ('leyte', '千九百四十四年十月、レイテおき海戦。史上最大の海戦で、戦艦武蔵が沈み、初めてかみかぜ特攻隊が出撃しました。',
              '1944年10月、レイテ沖海戦。史上最大の海戦で、戦艦武蔵が沈み、初めて神風特攻隊が出撃しました。', 0),
    ('iwojima', '千九百四十五年二月、いおうとうの戦い。にほんぐん約二万一千人のうち、約二万人が戦死。米軍の死傷者は、それを上回る約二万六千人でした。',
                '1945年2月、硫黄島の戦い。日本軍約2万1千人のうち、約2万人が戦死。米軍の死傷者は、それを上回る約2万6千人でした。', 0),
    ('okinawa', 'そして沖縄戦。約三か月の地上戦で、にちべい合わせて約二十万人が死亡。そのうち約九万四千人は、沖縄の住民でした。',
                'そして沖縄戦。約3か月の地上戦で、日米合わせて約20万人が死亡。そのうち約9万4千人は、沖縄の住民でした。', 0),
    ('end', '数字の一つひとつに、かけがえのない命がありました。',
            '数字の一つひとつに、かけがえのない命がありました。', 7.5),
]

def dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.05
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = 600; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, scenes, t = [], [], 0.0
for sid, say, sub, mn in SCRIPT:
    x = tts(say)
    sec = len(x) / SR
    dur = max(mn, LEAD + sec + TAIL)
    scenes.append({'id': sid, 'start': round(t, 3), 'dur': round(dur, 3),
                   'speech': [round(t + LEAD, 3), round(t + LEAD + sec, 3)], 'sub': sub})
    clips.append((t + LEAD, x))
    print(f'{t:6.2f}s  {sid:12s} speech {sec:5.2f}s  scene {dur:5.2f}s')
    t += dur
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track *= 0.85 / np.max(np.abs(track))
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が生成(手で編集しない)\nwindow.TIMELINE = ' +
            json.dumps({'total': TOTAL, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')

def ts(v):
    ms = int(round(v * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, s in enumerate(scenes, 1):
        a, b = s['speech']
        f.write(f"{i}\n{ts(a)} --> {ts(min(b + 0.4, TOTAL))}\n{s['sub']}\n\n")
print('total', TOTAL, 's')
