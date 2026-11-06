# -*- coding: utf-8 -*-
"""scenes.js の原稿を VOICEVOX(青山龍星)で1文ずつ合成し、実測した長さからシーン尺を決める。
出力: output/narration.wav, output/timings.json(render.html / capture.js が使う), output/subtitles_ja.srt
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(青山龍星 = 15.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル)
  VOICE_SPEED    話速(既定 1.15)
"""
import os, io, re, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICE_SPEED', '1.15'))
LEAD, GAP, TAIL = 0.5, 0.35, 0.9   # シーン頭の間 / 文と文の間 / シーン末の余韻
SUMMARY_EXTRA = 3.5                 # 最後のまとめ画面は余韻とクレジットのため長めに

def load_scenes():
    src = open(os.path.join(HERE, 'scenes.js'), encoding='utf-8').read()
    src = re.sub(r'^\s*//.*$', '', src, flags=re.M)
    return json.loads(src[src.index('['): src.rindex(']') + 1])

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
        name = next(c.name + '/' + st.name for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = SPEED
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(self.synth.synthesis(q, self.style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def trim(x):
    idx = np.where(np.abs(x) > 0.004)[0]
    return x[max(0, idx[0] - 1200): idx[-1] + 2400] if len(idx) else x

def main():
    scenes = load_scenes()
    engine = Voicevox()
    clips, timings, t = [], [], 0.0
    for s in scenes:
        c = t + LEAD; lines = []
        for ln in s['lines']:
            x, sr = engine(ln['read'])
            x = trim(resample(x, sr))
            f = min(600, len(x) // 4); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
            d = len(x) / SR
            clips.append((c, x)); lines.append({'a': round(c, 3), 'b': round(c + d, 3)})
            print(f'{c:6.2f}s  {d:4.1f}s  {ln["sub"]}')
            c += d + GAP
        dur = c - GAP + TAIL - t + (SUMMARY_EXTRA if s['type'] == 'summary' else 0)
        timings.append({'start': round(t, 3), 'dur': round(dur, 3), 'lines': lines})
        t += dur
    total = t
    track = np.zeros(int(np.ceil(total * SR)), dtype=np.float32)
    for c, x in clips:
        s0 = int(c * SR); track[s0:s0 + len(x)] += x[:len(track) - s0]
    track *= 0.85 / (np.max(np.abs(track)) or 1)
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    json.dump({'total': round(total, 3), 'scenes': timings}, open(os.path.join(OUT, 'timings.json'), 'w'), ensure_ascii=False, indent=1)

    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    n = 0
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for s, tm in zip(scenes, timings):
            for ln, c in zip(s['lines'], tm['lines']):
                n += 1; f.write(f"{n}\n{ts(c['a'])} --> {ts(min(c['b'] + 0.3, total))}\n{ln['sub']}\n\n")
    print(f'total {total:.2f}s  → output/narration.wav, output/timings.json, output/subtitles_ja.srt')

if __name__ == '__main__':
    main()
