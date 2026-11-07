# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX: 四国めたん)を合成し、字幕タイミング(captions.json / SRT)を書き出す。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0=あまあま 6=ツンツン 4=セクシー)
出力: output/narration.wav, output/captions.json, output/subtitles_ja.srt
"""
import os, io, re, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
TOTAL = 57.5
LEAD = 0.35  # シーン開始からナレーション開始までの間(秒)

# (開始秒, シーン長, 読み上げ原稿)  render.html の SCENES と対応させること
# 字幕は「|」で区切った単位でポップ表示する。【】で囲んだ部分は黄色で強調。
SCRIPT = [
    (0.0, 5.0,
     '月三万円の積立、三十年後にいくらになると思う？',
     '月3万円の積立、|30年後に【いくら】になると思う？'),
    (5.0, 6.5,
     'ただ貯金するだけなら、千八十万円。でも、年利五パーセントで運用すると……',
     'ただ貯金するだけなら|【1,080万円】。|でも、年利5%で運用すると……'),
    (11.5, 7.0,
     '約二千五百万円。差額の千四百万円は、複利が勝手に増やしてくれたお金よ。',
     '【約2,500万円】。|差額の1,400万円は|【複利】が勝手に増やしてくれたお金よ。'),
    (18.5, 11.5,
     '複利は、利益が利益を生む仕組み。十年で四百六十六万、二十年で千二百三十三万、三十年で二千四百九十七万。後半ほど一気に加速するの。',
     '複利は、【利益が利益を生む】仕組み。|10年で466万、|20年で1,233万、|30年で【2,497万】。|後半ほど【一気に加速】するの。'),
    (30.0, 9.5,
     'だから怖いのは、始めるのが遅れること。スタートが十年遅れると、同じ月三万円でも千二百三十三万。半分以下になっちゃう。',
     'だから怖いのは、|【始めるのが遅れる】こと。|スタートが10年遅れると、|同じ月3万円でも1,233万。|【半分以下】になっちゃう。'),
    (39.5, 10.5,
     '覚えておいて。お金が二倍になる年数は、七十二割る年利。五パーセントなら約十四年、七パーセントなら約十年。七十二の法則よ。',
     '覚えておいて。|お金が2倍になる年数は|【72 ÷ 年利】。|5%なら約14年、|7%なら約10年。|【72の法則】よ。'),
    (50.0, 7.5,
     '投資に元本保証はないけど、時間だけは誰にも増やせない。この動画を保存して、始める日を決めてね。',
     '投資に元本保証はないけど、|【時間】だけは誰にも増やせない。|この動画を【保存】して、|始める日を決めてね。'),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

def _find_ort():
    p = os.environ.get('VOICEVOX_ORT')
    if p: return p
    c = glob.glob('/home/user/vv/ort/**/libvoicevox_onnxruntime.so', recursive=True)
    return c[0] if c else 'libvoicevox_onnxruntime.so'

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=_find_ort())
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pitch_scale = 0.02          # ほんの少し明るく
        q.intonation_scale = 1.15     # 抑揚を強めにして引き込む
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.08
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback)')
    def __call__(self, text, speed):
        x, sr = self.tts(text, speed=speed)
        return x.astype(np.float32) / 32768.0, sr

try:
    engine = VoicevoxEngine()
except Exception as e:  # noqa
    print('VOICEVOX unavailable:', e)
    engine = OpenJtalkEngine()

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def synth(text, speed):
    x, sr = engine(text, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1000): idx[-1] + 2000]
    return x

def _weight(s):
    """字幕チャンクの発話長の重み: 文字数 + 句読点のポーズ分"""
    s = re.sub(r'[【】 ]', '', s)
    w = 0.0
    for ch in s:
        if ch in '、': w += 1.6
        elif ch in '。？！…': w += 2.2
        elif ch in ',': w += 0.0
        elif ch.isdigit() or ch in '%÷': w += 1.4
        else: w += 1.0
    return w

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
captions, srt = [], []
for si, (start, dur, text, sub) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.3
    speed = 1.12
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit: break
        speed = min(speed * (sec / limit) * 1.02, 1.25)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:16]}…')
    n = len(x); f = min(500, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s0 = int((start + LEAD) * SR); e0 = min(s0 + n, len(track))
    track[s0:e0] += x[:e0 - s0]
    # 字幕チャンクのタイミング(発話長を重みで按分)
    chunks = sub.split('|')
    ws = [_weight(c) for c in chunks]; tot = sum(ws)
    t = start + LEAD
    for c, w in zip(chunks, ws):
        d = sec * w / tot
        captions.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': c, 'scene': si})
        t += d
    srt.append((start + LEAD, start + LEAD + sec, re.sub(r'[【】]', '', sub.replace('|', ''))))

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.9
WAV = os.path.join(OUT, 'narration.wav')
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

with open(os.path.join(OUT, 'captions.json'), 'w', encoding='utf-8') as f:
    json.dump(captions, f, ensure_ascii=False, indent=1)
print('wrote captions.json', len(captions), 'chunks')

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(srt, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
print('wrote subtitles_ja.srt')
