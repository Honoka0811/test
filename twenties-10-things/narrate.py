# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX: 四国めたん)を合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0=あまあま, 6=ツンツン, 4=セクシー)
"""
import sys, os, io, wave, glob, json, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'twenties_10.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'twenties_10_narrated.mp4')
WAV = os.path.join(OUT, 'narration.wav')
MIX = os.path.join(OUT, 'mix.wav')
SRT = os.path.join(OUT, 'subtitles_ja.srt')
SR = 48000

# シーン構成(render.html の SCENES と一致させる)
TITLE_DUR, ITEM_DUR, OUTRO_DUR = 5.0, 5.6, 5.5
TOTAL = TITLE_DUR + 10 * ITEM_DUR + OUTRO_DUR   # 66.5 秒
LEAD = 0.35   # シーン開始からナレーション開始までの間

# (読み上げ原稿, 字幕表示用テキスト)
LINES = [
    ('二十代のうちにやっておくべきこと、十選。さくっと紹介します!',
     '20代のうちにやっておくべきこと10選。さくっと紹介します!'),
    ('一つ目、海外に行く。知らない世界を見ると、価値観がぐっと広がります。',
     '①海外に行く。知らない世界を見ると、価値観がぐっと広がります。'),
    ('二つ目、本を読む習慣。月に一冊でも、十年で百二十冊になります。',
     '②本を読む習慣。月に1冊でも、10年で120冊になります。'),
    ('三つ目、お金の勉強。貯金と投資は、早く始めた人が有利です。',
     '③お金の勉強。貯金と投資は、早く始めた人が有利です。'),
    ('四つ目、体を鍛える。体力は、三十代以降の最大の資産です。',
     '④体を鍛える。体力は、30代以降の最大の資産です。'),
    ('五つ目、失敗を恐れず挑戦する。二十代の失敗は、全部ネタになります。',
     '⑤失敗を恐れず挑戦する。20代の失敗は、全部ネタになります。'),
    ('六つ目、スキルを身につける。英語やプログラミングは、一生ものです。',
     '⑥スキルを身につける。英語やプログラミングは、一生ものです。'),
    ('七つ目、人とのつながりを広げる。チャンスは、人が運んできます。',
     '⑦人とのつながりを広げる。チャンスは、人が運んできます。'),
    ('八つ目、一人暮らしをする。家事とお金の管理で、生活力が爆上がりします。',
     '⑧一人暮らしをする。家事とお金の管理で、生活力が爆上がりします。'),
    ('九つ目、家族との時間。親と過ごせる時間は、意外と少ないんです。',
     '⑨家族との時間。親と過ごせる時間は、意外と少ないんです。'),
    ('十個目、自分の好きを見つける。没頭できる趣味が、人生を豊かにします。',
     '⑩自分の「好き」を見つける。没頭できる趣味が、人生を豊かにします。'),
    ('二十代は、人生の土台をつくる十年。今日から一つ、始めてみませんか?',
     '20代は、人生の土台をつくる10年。今日から1つ、始めてみませんか?'),
]
STARTS = [0.0] + [TITLE_DUR + ITEM_DUR * i for i in range(10)] + [TITLE_DUR + 10 * ITEM_DUR]
DURS = [TITLE_DUR] + [ITEM_DUR] * 10 + [OUTRO_DUR]

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
        self.name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', self.name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pitch_scale = 0.02
        q.intonation_scale = 1.15     # 少し抑揚を強めて元気な感じに
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
        self.name = 'Open JTalk'
        print('engine: Open JTalk (fallback)')
    def __call__(self, text, speed):
        x, sr = self.tts(text, speed=speed, half_tone=2.0)
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

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for li, ((text, sub), start, dur) in enumerate(zip(LINES, STARTS, DURS)):
    limit = dur - LEAD - 0.3
    speed = 1.15  # 基準速度: テンポよく
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.45)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:20]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR); e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR, sub))

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)
json.dump([{'start': a, 'end': b, 'text': t} for a, b, t in cues], open(os.path.join(OUT, 'cues.json'), 'w'), ensure_ascii=False, indent=1)

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(SRT, 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
print('wrote', SRT)

# ---------- BGM をダッキングしながらミックス(ステレオ) ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)                      # (2, n)
music = music[:, :len(track)] if music.shape[1] >= len(track) else np.pad(music, ((0, 0), (0, len(track) - music.shape[1])))
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.88)   # リリース ≈ 0.4 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.50, 0.22     # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = music * gain + track[None, :]
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
with wave.open(MIX, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed.T * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

if os.path.exists(SRC):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
    print('wrote', DST)
else:
    print('video not found, skipped mux:', SRC)
