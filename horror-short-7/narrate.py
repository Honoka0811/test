# -*- coding: utf-8 -*-
"""VOICEVOX(四国めたん)で台本を合成し、output/segs.npz(行ごとの音声)と timeline.json を書き出す。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT(省略時は既定パス)"""
import os, io, glob, json, wave
import numpy as np
from script import LINES

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
STYLES = {'n': 2, 'w': 36, 'h': 37, 'g': 2}   # 四国めたん ノーマル / ささやき / ヒソヒソ / (g=祖母の台詞。ノーマルを低くゆっくり)
PARAMS = {'n': dict(speed=1.04, pitch=-0.03, into=0.9, vol=1.0),
          'w': dict(speed=0.8, pitch=-0.07, into=1.0, vol=1.8),
          'h': dict(speed=0.66, pitch=-0.07, into=1.0, vol=2.0),
          'g': dict(speed=0.9, pitch=-0.09, into=0.8, vol=1.0)}
START = 0.4

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
    s = engine(); segs, tl, t = {}, [], START
    for lid, kind, st, text, disp, gap in LINES:
        p = PARAMS[st]; sid = STYLES[st]
        q = s.create_audio_query(text, sid)
        q.speed_scale = p['speed']; q.pitch_scale = p['pitch']; q.intonation_scale = p['into']
        q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.05
        with wave.open(io.BytesIO(s.synthesis(q, sid))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x).astype(np.float32)
        x *= p['vol']; dur = len(x) / SR
        print(f'{t:6.2f}  {dur:5.2f}s  [{kind}/{st}] {q.kana}')
        tl.append(dict(id=lid, kind=kind, start=round(t, 3), end=round(t + dur, 3), text=disp))
        segs[lid] = x; t += dur + gap
    os.makedirs(os.path.join(HERE, 'output'), exist_ok=True)
    np.savez(os.path.join(HERE, 'output', 'segs.npz'), **segs)
    json.dump(dict(duration=round(t, 2), lines=tl), open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    print('total', round(t, 2))

if __name__ == '__main__':
    main()
