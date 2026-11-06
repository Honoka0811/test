# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)をフレーズ単位で合成し、タイムライン(JSON)と字幕(SRT)を書き出す。
フレーズごとに合成するので、テロップをナレーションと正確に同期できる。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT    libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS   *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_DICT   Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE  スタイルID(既定 2 = 四国めたん ノーマル。0=あまあま 6=ツンツン 4=セクシー)
  VOICEVOX_SPEED  話速(既定 1.15)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
LEAD = 0.30        # シーン開始からナレーション開始までの間
GAP = 0.12         # フレーズ間の間
TAIL = 0.55        # シーン末尾の余白(ナレーション終了→次シーン)

# シーン定義: (id, 最低尺[秒], [(読み上げテキスト, 画面テロップ), ...])
# テロップの *〜* は黄色ハイライト。読み上げテキストは VOICEVOX 向けに表記を調整している。
SCENES = [
    ('hook', 3.2, [
        ('卵かけごはん、まだ普通に混ぜてる？', '卵かけごはん\nまだ*普通に*混ぜてる？'),
        ('それ、めちゃくちゃ損してます。', 'それ、*めちゃくちゃ損*してます'),
    ]),
    ('promise', 3.6, [
        ('卵一個で、ふわとろが十倍になる裏ワザ。', '卵1個で*ふわとろ10倍*の裏ワザ'),
        ('三十秒で教えます。', '*30秒*で教えます'),
    ]),
    ('step1', 4.2, [
        ('まず、卵を割って、', 'まず卵を割って'),
        ('白身と黄身を分けます。', '*白身*と*黄身*を分ける'),
    ]),
    ('step2', 7.5, [
        ('熱々のごはんに、白身だけを入れて、', '熱々ごはんに*白身だけ*入れて'),
        ('三十秒、ひたすら混ぜる！', '*30秒*ひたすら混ぜる！'),
        ('泡立って白くなったら、成功です。', '泡立って*白くなったら*成功'),
    ]),
    ('step3', 7.5, [
        ('真ん中にくぼみを作って、黄身をポン。', '真ん中にくぼみ → *黄身をポン*'),
        ('醤油は、黄身の上に三滴だけ。', '醤油は黄身の上に*3滴だけ*'),
        ('仕上げに、バターをひとかけら。', '仕上げに*バター*をひとかけら'),
    ]),
    ('payoff', 5.0, [
        ('黄身を崩した瞬間、', '黄身を崩した瞬間…'),
        ('ふわっ、とろっ、口の中が天国です。', '*ふわっ、とろっ*\n口の中が天国'),
    ]),
    ('cta', 4.6, [
        ('やってみたら、感想をコメントで教えてね。', 'やってみたら*コメント*で教えてね'),
        ('保存して、今夜試してみて。', '*保存*して今夜試してみて'),
    ]),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d and os.path.isdir(d): return d
    for c in ['/home/user/vv/dict/open_jtalk_dic_utf_8-1.11', os.path.join(HERE, 'open_jtalk_dic_utf_8-1.11')]:
        if os.path.isdir(c): return c
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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        self.speed = float(os.environ.get('VOICEVOX_SPEED', '1.15'))
        self.name = next((c.name + '(' + st.name + ')') for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', self.name, 'speed', self.speed)
    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = self.speed
        q.intonation_scale = 1.15     # 抑揚を少し強めて元気な印象に
        q.pre_phoneme_length = 0.03
        q.post_phoneme_length = 0.06
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        # 前後の無音をトリム
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx): x = x[max(0, idx[0] - 600): idx[-1] + 1800]
        f = min(400, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x

engine = Voicevox()

# ---- 合成してタイムラインを組む ----
clips = []   # (scene_idx, chunk_idx, audio)
timeline = {'engine': engine.name, 'scenes': []}
t = 0.0
for sid, min_dur, chunks in SCENES:
    audios = [engine(text) for text, _ in chunks]
    speech = sum(len(a) for a in audios) / SR + GAP * (len(audios) - 1)
    dur = max(min_dur, LEAD + speech + TAIL)
    scene = {'id': sid, 'start': round(t, 3), 'dur': round(dur, 3), 'captions': []}
    ct = t + LEAD
    for (text, cap), a in zip(chunks, audios):
        scene['captions'].append({'start': round(ct, 3), 'end': round(ct + len(a) / SR, 3), 'text': cap, 'read': text})
        clips.append((ct, a))
        ct += len(a) / SR + GAP
    print(f"{sid:8s} {t:5.1f}s  dur {dur:4.1f}s  speech {speech:4.1f}s")
    timeline['scenes'].append(scene)
    t += dur
TOTAL = round(t, 3)
timeline['total'] = TOTAL
print('total', TOTAL, 's')

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for st, a in clips:
    s = int(st * SR); track[s:s + len(a)] += a
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(timeline, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:   # render.html が file:// から読むため
    f.write('window.TIMELINE = ' + json.dumps(timeline, ensure_ascii=False) + ';\n')

def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timeline['scenes']:
        for c in sc['captions']:
            f.write(f"{i}\n{_ts(c['start'])} --> {_ts(min(c['end'] + 0.25, TOTAL))}\n{c['text'].replace('*', '').replace(chr(10), ' ')}\n\n"); i += 1
print('wrote output/narration.wav, timeline.json, timeline.js, subtitles_ja.srt')
