# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん ノーマル)を文ごとに合成し、
合成結果の長さからシーン尺を決めて output/timeline.js(render.html が読む)と字幕 SRT を書き出す。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま、6 = ツンツン)
  VOICEVOX_SPEED 話速(既定 1.27)
"""
import os, io, wave, glob, json
import numpy as np
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.27'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
LEAD = 0.45   # シーン開始 → 最初の発話
GAP = 0.15    # 文と文の間
TAIL = 0.6   # 最後の発話 → 次のシーン
OUTRO_TAIL = 2.2

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    pyopenjtalk.g2p('あ')  # 辞書が無ければここでダウンロードされる
    for base in {os.path.dirname(pyopenjtalk.__file__)} | set(glob.glob('/usr/local/lib/python3*/*-packages/pyopenjtalk')):
        p = os.path.join(base, 'open_jtalk_dic_utf_8-1.11')
        if os.path.exists(os.path.join(p, 'sys.dic')): return p
    raise FileNotFoundError('Open JTalk dictionary not found')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
name = next((c.name + '/' + st.name) for c in synth.metas() for st in c.styles if st.id == STYLE)
print('engine: VOICEVOX', name, 'speed', SPEED)

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.pitch_scale = 0.0
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.08
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx): x = x[max(0, idx[0] - 600): idx[-1] + 2400]
    f = min(480, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, scenes, caps = [], [], []
t = 0.0
for si, sc in enumerate(SCENES):
    start = t
    t += LEAD if si else 0.35
    for li, (say, show) in enumerate(sc['lines']):
        x = tts(say)
        d = len(x) / SR
        clips.append((t, x))
        caps.append({'a': round(t, 3), 'b': round(t + d, 3), 'text': show, 'scene': si})
        t += d + (GAP if li < len(sc['lines']) - 1 else 0)
    t += OUTRO_TAIL if sc['id'] == 'outro' else TAIL
    scenes.append({'id': sc['id'], 'start': round(start, 3), 'dur': round(t - start, 3)})
    print(f"{sc['id']:6s} {start:6.2f}s  dur {t - start:5.2f}s")
TOTAL = round(t, 3)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for st, x in clips:
    s = int(st * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が生成(手で編集しない)\nwindow.TIMELINE = ' +
            json.dumps({'total': TOTAL, 'scenes': scenes, 'caps': caps}, ensure_ascii=False, indent=1) + ';\n')

def _ts(v):
    h = int(v // 3600); m = int(v % 3600 // 60); s = v % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(caps, 1):
        f.write(f"{i}\n{_ts(c['a'])} --> {_ts(min(c['b'] + 0.2, TOTAL))}\n{c['text']}\n\n")
print(f'total {TOTAL:.2f}s  -> output/narration.wav, output/timeline.js, output/subtitles_ja.srt')
