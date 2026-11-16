# -*- coding: utf-8 -*-
"""VOICEVOX(四国めたん)で台本を合成し、output/narration.wav と timeline.json を書き出す。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT(省略時は既定パス)"""
import os, io, glob, json, wave
import numpy as np
from script import LINES

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
STYLES = {'n': 2, 'w': 36, 'h': 37}          # 四国めたん ノーマル / ささやき / ヒソヒソ
PARAMS = {'n': dict(speed=1.03, pitch=-0.03, into=0.9, vol=1.0),
          'w': dict(speed=0.92, pitch=-0.02, into=1.0, vol=1.7),
          'h': dict(speed=0.78, pitch=-0.04, into=1.0, vol=2.0)}
START = 0.35

def engine():
    import pyopenjtalk
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    d = os.environ.get('VOICEVOX_DICT') or os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
    if not os.path.isdir(d): pyopenjtalk.g2p('あ')
    so = os.environ.get('VOICEVOX_ORT') or glob.glob('/home/user/vv/ort/*/lib/libvoicevox_onnxruntime.so*')[0]
    s = Synthesizer(Onnxruntime.load_once(filename=so), OpenJtalk(d))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m: s.load_voice_model(m)
    return s

def main():
    s = engine()
    parts, tl, t = [], [], START
    for lid, st, text, sub, gap in LINES:
        p = PARAMS[st]; sid = STYLES[st]
        q = s.create_audio_query(text, sid)
        q.speed_scale = p['speed']; q.pitch_scale = p['pitch']; q.intonation_scale = p['into']
        q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.05
        with wave.open(io.BytesIO(s.synthesis(q, sid))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x).astype(np.float32)
        x *= p['vol']
        dur = len(x) / SR
        print(f'{t:6.2f}  {dur:5.2f}s  [{st}] {q.kana}')
        tl.append(dict(id=lid, style=st, start=round(t, 3), end=round(t + dur, 3), sub=sub))
        parts.append((t, x)); t += dur + gap
    total = round(t, 2)
    track = np.zeros(int(total * SR), dtype=np.float32)
    for t0, x in parts:
        i = int(t0 * SR); track[i:i + len(x)] += x[:len(track) - i]
    os.makedirs(os.path.join(HERE, 'output'), exist_ok=True)
    np.save(os.path.join(HERE, 'output', 'narration.npy'), track)
    with wave.open(os.path.join(HERE, 'output', 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())
    json.dump(dict(duration=total, lines=tl), open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    print('total', total)

if __name__ == '__main__':
    main()
