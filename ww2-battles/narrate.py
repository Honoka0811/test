# -*- coding: utf-8 -*-
"""シーンごとのナレーション(VOICEVOX:青山龍星)を合成し、BGM(air.py「G線上のアリア」)を
ダッキングしながらミックスする。字幕用に output/cues.js(焼き込み字幕)と output/subtitles_ja.srt も書き出す。
voicevox_core が無い環境では Open JTalk にフォールバックする(その場合は青山龍星の声にはならない)。
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル)
"""
import sys, os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
LEAD = 0.7  # シーン開始からナレーション開始までの間

# シーン長(render.html の INTRO / CARD / SUMMARY / OUTRO と一致させる)
INTRO, CARD, SUMMARY, OUTRO = 7, 10, 9, 6

# (読み上げ原稿, 字幕表示)
INTRO_LINE = ('第二次世界大戦の激戦を、時代順に振り返ります。',
              '第二次世界大戦の激戦を、時代順に振り返ります。')
BATTLE_LINES = [
    ('レニングラード包囲戦。八百七十二日に及ぶ包囲で、市民の死者は百万人ともいわれます。',
     'レニングラード包囲戦。872日に及ぶ包囲で、市民の死者は100万人ともいわれます。'),
    ('ミッドウェー海戦。日本は主力空母四隻を一度に失い、戦局の転換点となりました。',
     'ミッドウェー海戦。日本は主力空母4隻を一度に失い、戦局の転換点となりました。'),
    ('スターリングラード攻防戦。激しい市街戦の末、ドイツ第六軍が降伏。死傷者は両軍で約二百万人。',
     'スターリングラード攻防戦。激しい市街戦の末、ドイツ第6軍が降伏。死傷者は両軍で約200万人。'),
    ('ガダルカナル島の戦い。補給を断たれた日本軍は約二万人が死亡。その多くが飢えと病によるものでした。',
     'ガダルカナル島の戦い。補給を断たれた日本軍は約2万人が死亡。その多くが飢えと病によるものでした。'),
    ('クルスクの戦い。両軍の戦車、約六千両が激突した、史上最大級の戦車戦です。',
     'クルスクの戦い。両軍の戦車、約6千両が激突した、史上最大級の戦車戦です。'),
    ('ノルマンディー上陸作戦。初日だけで約十五万六千人の連合軍が、フランスの海岸に上陸しました。',
     'ノルマンディー上陸作戦。初日だけで約15万6千人の連合軍が、フランスの海岸に上陸しました。'),
    ('硫黄島の戦い。日本の守備隊は約二万人が戦死。米軍の死傷者は、日本軍を上回りました。',
     '硫黄島の戦い。日本の守備隊は約2万人が戦死。米軍の死傷者は、日本軍を上回りました。'),
    ('沖縄戦。犠牲者は約二十万人。そのうち一般の住民が、約九万四千人にのぼります。',
     '沖縄戦。犠牲者は約20万人。そのうち一般の住民が、約9万4千人にのぼります。'),
    ('ベルリンの戦い。ソ連軍の総攻撃で首都は陥落し、ヨーロッパの戦争は終わりを迎えました。',
     'ベルリンの戦い。ソ連軍の総攻撃で首都は陥落し、ヨーロッパの戦争は終わりを迎えました。'),
]
SUMMARY_LINE = ('わずか六年の間に、世界中でこれほどの激戦が繰り広げられました。',
                'わずか6年の間に、世界中でこれほどの激戦が繰り広げられました。')
OUTRO_LINE = ('すべての犠牲者に、哀悼の意を込めて。', 'すべての犠牲者に、哀悼の意を込めて。')

SCRIPT = [(0, INTRO, *INTRO_LINE)]
for i, l in enumerate(BATTLE_LINES):
    SCRIPT.append((INTRO + i * CARD, CARD, *l))
t_sum = INTRO + len(BATTLE_LINES) * CARD
SCRIPT.append((t_sum, SUMMARY, *SUMMARY_LINE))
SCRIPT.append((t_sum + SUMMARY, OUTRO, *OUTRO_LINE))
TOTAL = t_sum + SUMMARY + OUTRO

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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name); self.name = 'VOICEVOX:' + name.split('/')[0]
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback)'); self.name = 'Open JTalk'
    def __call__(self, text, speed):
        x, sr = self.tts(text, speed=speed, half_tone=-1.5)
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
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for start, dur, text, sub in SCRIPT:
    limit = dur - LEAD - 0.4
    speed = 1.0  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.35)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:16]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR); e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((round(start + LEAD, 3), round(min(start + LEAD + n / SR + 0.3, start + dur - 0.3), 3), sub))

track = track / (np.max(np.abs(track)) or 1) * 0.85
def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)
write_wav(os.path.join(OUT, 'narration.wav'), track)

with open(os.path.join(OUT, 'cues.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が生成(字幕)  [開始秒, 終了秒, テキスト]\nwindow.CUES = ' + json.dumps(cues, ensure_ascii=False) + ';\n'
            + 'window.VOICE_CREDIT = ' + json.dumps(engine.name, ensure_ascii=False) + ';\n')
def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(b)}\n{t}\n\n')
with open(os.path.join(OUT, 'engine.txt'), 'w') as f:
    f.write(engine.name + '\n')

# ---------- BGM をダッキングしながらミックス ----------
import air
music = air.generate(TOTAL)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
write_wav(os.path.join(OUT, 'bgm.wav'), music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.93)   # リリース ≈ 0.7 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.45, 0.20   # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 5
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)
