# -*- coding: utf-8 -*-
"""シーンごとのナレーション(VOICEVOX:四国めたん)を合成し、BGM(bgm.py)をダッキングしながらミックスする。
出力: output/narration.wav, output/mix.wav, output/subtitles_ja.srt, output/cues.js(render.html の焼き込み字幕用)
使い方: python3 narrate.py   → その後 node capture.js で映像化+音声を多重化
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま)
"""
import os, io, re, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)

SR = 48000
TOTAL = 66.0
LEAD = 0.25  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 読み上げ原稿, 字幕テキスト)  render.html の SCENES と対応
SCRIPT = [
    (0, 6.5,
     'ノーベル賞の賞金って、百二十五年も払い続けているのに、なぜ尽きないと思いますか?',
     'ノーベル賞の賞金って、125年も払い続けているのに、なぜ尽きないと思いますか?'),
    (6.5, 9,
     '始まりは、ダイナマイト王、アルフレッド・ノーベルの遺言。全財産の九十四パーセント、約三千百万クローナが基金になりました。',
     '始まりは、ダイナマイト王アルフレッド・ノーベルの遺言。全財産の94%、約3100万クローナが基金になりました。'),
    (15.5, 6.5,
     '最初の運用は、国債や不動産など、安全なものだけ。しかも税金まで重くのしかかります。',
     '最初の運用は、国債や不動産など安全なものだけ。しかも税金まで重くのしかかります。'),
    (22, 7.5,
     'そこにインフレが追い打ち。千九百四十五年ごろ、賞金の実質的な価値は、三分の一以下に落ち込みました。',
     'そこにインフレが追い打ち。1945年ごろ、賞金の実質的な価値は3分の1以下に落ち込みました。'),
    (29.5, 8,
     '転機は戦後です。千九百四十六年にスウェーデンで非課税となり、千九百五十三年には、株式への投資が自由になりました。',
     '転機は戦後です。1946年にスウェーデンで非課税となり、1953年には株式への投資が自由になりました。'),
    (37.5, 11,
     'ここから資産は右肩上がり。二千十二年に約三十億、二千二十二年に五十八億、二千二十五年末には六十七億クローナ。設立時の、およそ二百倍です。',
     'ここから資産は右肩上がり。2012年に約30億、2022年に58億、2025年末には67億クローナ。設立時のおよそ200倍です。'),
    (48.5, 10,
     '賞金も、二千十二年には金融危機の影響で八百万クローナに減額。でもその後は回復し、二千二十六年は、過去最高の千二百万クローナです。',
     '賞金も、2012年には金融危機の影響で800万クローナに減額。でもその後は回復し、2026年は過去最高の1200万クローナです。'),
    (58.5, 7.5,
     '守るだけでは、お金は減っていく。増やし続ける仕組みが、ノーベル賞を支えているんです。',
     '守るだけでは、お金は減っていく。増やし続ける仕組みが、ノーベル賞を支えているんです。'),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
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
        q.intonation_scale = 1.15   # ショート向けに抑揚をやや強める
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

engine = VoicevoxEngine()

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def synth(text, speed):
    x, sr = engine(text, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

def split_sub(text):
    """字幕を句読点で 1〜2 行ぶんの塊に分ける"""
    parts = [p for p in re.split(r'(?<=[。!?])', text) if p]
    out = []
    for p in parts:
        if len(p) <= 30: out.append(p); continue
        # 長い文は読点で分割
        buf = ''
        for q in re.split(r'(?<=、)', p):
            if len(buf) + len(q) > 30 and buf: out.append(buf); buf = q
            else: buf += q
        if buf: out.append(buf)
    # 短すぎる塊(8文字未満)は次の塊とつなげる
    merged = []
    for c in out:
        if merged and len(merged[-1]) < 8 and len(merged[-1]) + len(c) <= 34: merged[-1] += c
        else: merged.append(c)
    return merged

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for start, dur, text, sub in SCRIPT:
    limit = dur - LEAD - 0.25
    speed = 1.25  # ショート向けにテンポよく(全シーン共通の基準)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit: break
        speed = min(speed * (sec / limit) * 1.02, 1.45)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {sub[:18]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR); e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    # 字幕: 文字数に比例して時間を割り振る
    chunks = split_sub(sub)
    a0, span = start + LEAD, n / SR
    tot = sum(len(c) for c in chunks); acc = 0
    for i, c in enumerate(chunks):
        ca = a0 + span * acc / tot; acc += len(c)
        cb = a0 + span * acc / tot if i < len(chunks) - 1 else min(a0 + span + 0.3, start + dur)
        cues.append({'a': round(ca, 3), 'b': round(cb, 3), 'text': c})

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)
write_wav(os.path.join(OUT, 'narration.wav'), track)

with open(os.path.join(OUT, 'cues.js'), 'w', encoding='utf-8') as f:
    f.write('window.CUES = ' + json.dumps(cues, ensure_ascii=False) + ';\n')
def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{_ts(c['a'])} --> {_ts(c['b'])}\n{c['text']}\n\n")
print('wrote cues.js / subtitles_ja.srt', len(cues), 'cues')

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
write_wav(os.path.join(OUT, 'bgm.wav'), music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.20
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)
