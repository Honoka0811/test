# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、行ごとの実測タイミングを timings.json に書き出す。
映像(render.html)はこのタイミングに合わせて描画される。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np
from script import LINES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
VV = '/home/user/vv'
SR = 48000
SPEED = 1.12
START = 0.25      # 動画冒頭の無音
TAIL = 2.2        # 最後の行のあとの余白

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text, pitch=0.0, intonation=1.15):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.pitch_scale = pitch
    q.intonation_scale = intonation
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.08
    kana = ''.join(m.text for ap in q.accent_phrases for m in ap.moras)
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = min(400, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x, kana

clips, cues, t = [], [], START
for ln in LINES:
    x, kana = tts(ln['say'], ln.get('pitch', 0.0), ln.get('into', 1.15))
    d = len(x) / SR
    cues.append({'id': ln['id'], 'start': round(t, 3), 'end': round(t + d, 3), 'text': ln['sub']})
    clips.append((t, x))
    print(f"{t:6.2f}s +{d:4.2f}s  {ln['id']:<8} {kana}")
    t += d + ln.get('gap', 0.35)
total = cues[-1]['end'] + TAIL

track = np.zeros(int(total * SR) + 1, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

json.dump({'duration': round(total, 3), 'cues': cues}, open(os.path.join(OUT, 'timings.json'), 'w'), ensure_ascii=False, indent=1)

def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{ts(c['start'])} --> {ts(c['end'] + 0.2)}\n{c['text'].replace('|', '')}\n\n")
print(f'total {total:.2f}s -> output/narration.wav, timings.json, subtitles_ja.srt')
