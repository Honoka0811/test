# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX(四国めたん ノーマル)で合成し、
ナレーションの長さに合わせてシーン尺を決めて timeline.js(render.html 用)と字幕 SRT を書き出す。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, re, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.15     # 話速(全シーン共通)
LEAD = 0.35      # シーン開始から読み始めまで
TAIL = 0.55      # 読み終わりから次のシーンまで

# (シーンID, 読み上げ原稿, 字幕表記)  シーンIDは render.html の SCENE_FUNCS と対応
SCRIPT = [
    ('title',
     'わたくし、四国めたんが、世界を変えた化学の大発見を、六つ紹介しますわ。',
     'わたくし四国めたんが、世界を変えた化学の大発見を6つ紹介しますわ。'),
    ('periodic',
     'まずは千八百六十九年、メンデレーエフの周期表。元素を規則正しく並べ、まだ見つかっていない元素の存在まで予言しましたの。',
     'まずは1869年、メンデレーエフの周期表。元素を規則正しく並べ、まだ見つかっていない元素の存在まで予言しましたの。'),
    ('radium',
     '千八百九十八年、キュリー夫妻がポロニウムとラジウムを発見。放射能の研究は、がん治療や原子力へとつながりました。',
     '1898年、キュリー夫妻がポロニウムとラジウムを発見。放射能の研究は、がん治療や原子力へとつながりました。'),
    ('haber',
     '千九百九年、ハーバーが空気中の窒素からアンモニアを合成。肥料を大量に作れるようになり、今では世界人口の約半分の食料を支えているとも言われますわ。',
     '1909年、ハーバーが空気中の窒素からアンモニアを合成。肥料を大量に作れるようになり、今では世界人口の約半分の食料を支えているとも言われますわ。'),
    ('penicillin',
     '千九百二十八年、フレミングがアオカビからペニシリンを発見。人類初の抗生物質は、数えきれない命を救いました。',
     '1928年、フレミングがアオカビからペニシリンを発見。人類初の抗生物質は、数えきれない命を救いました。'),
    ('nylon',
     '千九百三十五年、カロザースがナイロンを合成。石油から作る、合成繊維とプラスチックの時代が始まります。',
     '1935年、カロザースがナイロンを合成。石油から作る、合成繊維とプラスチックの時代が始まります。'),
    ('battery',
     '千九百八十五年、よしのあきらさんがリチウムイオン電池の原型を開発。スマホも電気自動車も、この発明なしには動きませんわ。',
     '1985年、吉野彰さんがリチウムイオン電池の原型を開発。スマホも電気自動車も、この発明なしには動きませんわ。'),
    ('outro',
     '化学の発見が、わたくしたちの今の暮らしを作っているのですわ。',
     '化学の発見が、わたくしたちの今の暮らしを作っているのですわ。'),
]
MIN_DUR = {'title': 5.0, 'outro': 5.5}  # 演出上の最低尺

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
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

def split_sub(text, a, b):
    """字幕を句点ごとに分け、文字数比で時間を割り振る(長い文は読点でさらに分割)"""
    parts = [p for p in re.split(r'(?<=。)', text) if p]
    out = []
    for p in parts:
        if len(p) > 30:
            sub = [s for s in re.split(r'(?<=、)', p) if s]
            # 読点で 2 つにまとめる(なるべく均等)
            best, cut = 1e9, 1
            for i in range(1, len(sub)):
                d = abs(len(''.join(sub[:i])) - len(''.join(sub[i:])))
                if d < best: best, cut = d, i
            out += [''.join(sub[:cut]), ''.join(sub[cut:])] if len(sub) > 1 else [p]
        else:
            out.append(p)
    total = sum(len(p) for p in out)
    cues, t = [], a
    for p in out:
        d = (b - a) * len(p) / total
        cues.append((t, t + d, p)); t += d
    return cues

clips, scenes, cues = [], [], []
t = 0.0
for sid, read, sub in SCRIPT:
    x = tts(read)
    sec = len(x) / SR
    dur = round(max(LEAD + sec + TAIL, MIN_DUR.get(sid, 0)), 2)
    scenes.append({'id': sid, 's': round(t, 3), 'd': dur})
    clips.append((t + LEAD, x))
    cues += split_sub(sub, t + LEAD, t + LEAD + sec)
    print(f'{t:5.1f}s  {sid:10s} voice {sec:4.1f}s  scene {dur:4.1f}s')
    t += dur
TOTAL = round(t + 0.5, 2)  # 最後に少し余韻
scenes[-1]['d'] = round(TOTAL - scenes[-1]['s'], 2)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for st, x in clips:
    s = int(st * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

tl = {'total': TOTAL, 'scenes': scenes, 'subs': [{'a': round(a, 3), 'b': round(b, 3), 't': s} for a, b, s in cues]}
with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成(手で編集しない)\nwindow.TIMELINE = ' + json.dumps(tl, ensure_ascii=False, indent=1) + ';\n')

def _ts(v):
    ms = int(round(v * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, s) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(b)}\n{s}\n\n')
print(f'total {TOTAL}s  wrote narration.wav, timeline.js, subtitles_ja.srt')
