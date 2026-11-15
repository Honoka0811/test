# -*- coding: utf-8 -*-
"""VOICEVOX(四国めたん)でシーンごとのナレーションを合成し、
音声の長さからシーンの尺を決めて output/timeline.json・narration.wav・subtitles_ja.srt を書き出す。
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVM   0.vvm(四国めたん収録)のパス
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave
import numpy as np
from content import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
VV = '/home/user/vv'
SR = 48000
LEAD = 0.30      # シーン開始 → 発話開始
TAIL = 0.40      # 発話終了 → 次のシーン
MIN_DUR = {'intro': 3.2, 'item': 4.6, 'outro': 4.2}
SPEED = 1.25

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
      f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
syn = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
with VoiceModelFile.open(os.environ.get('VOICEVOX_VVM', f'{VV}/vvms/0.vvm')) as m:
    syn.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + s.name for c in syn.metas() for s in c.styles if s.id == STYLE))

def tts(text, kind):
    q = syn.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.pitch_scale = 0.02 if kind != 'item' else 0.0   # 冒頭と締めは少し明るめ
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(syn.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = 480; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, timeline, t = [], [], 0.0
for sc in SCENES:
    x = tts(sc['read'], sc['kind'])
    sec = len(x) / SR
    dur = round(max(MIN_DUR[sc['kind']], LEAD + sec + TAIL), 2)
    timeline.append(dict(start=round(t, 3), dur=dur, vs=round(t + LEAD, 3), ve=round(t + LEAD + sec, 3), sub=sc['sub']))
    clips.append((t + LEAD, x))
    print(f"{t:6.2f}s  dur {dur:4.2f}  voice {sec:4.2f}s  {sc['sub'][:20]}")
    t += dur
TOTAL = round(t + 0.6, 2)   # 最後に少し余韻

track = np.zeros(int(TOTAL * SR), np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track *= 0.85 / (np.max(np.abs(track)) or 1)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(total=TOTAL, scenes=timeline), f, ensure_ascii=False, indent=1)

def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round(v % 1 * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, sc in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(sc['vs'])} --> {ts(min(sc['ve'] + 0.3, TOTAL))}\n{sc['sub']}\n\n")
print(f'total {TOTAL}s → output/narration.wav, timeline.json, subtitles_ja.srt')
