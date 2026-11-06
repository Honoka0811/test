# -*- coding: utf-8 -*-
"""シーンごとのナレーションを合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
既定は VOICEVOX(青山龍星)。voicevox_core が無い環境では Open JTalk にフォールバックする。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル。11 = 玄野武宏 ノーマル)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'yen_per_second.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'yen_per_second_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 67.0
LEAD = 0.35  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応。読み上げ用に数字は漢数字
SCRIPT = [
    (0,    6.5, '一秒に一円ずつ数えます。一兆円まで、何年かかると思いますか？'),
    (6.5,  5.5, 'まず一万円。二時間四十六分四十秒。まだ余裕ですね。'),
    (12,   6.5, '百万円。十一日と十三時間。寝ずに数えて、十一日です。'),
    (18.5, 6.5, '一億円。三年と二か月。数え終わるころには、三つ歳をとっています。'),
    (25,   7,   '十億円。三十一年八か月。生まれた瞬間から数え始めて、終わるのは三十一歳です。'),
    (32,   8,   '一兆円。三万一千七百年。数え始めたのは、縄文時代よりずっと前、旧石器時代です。'),
    (40,   9,   '国家予算、百十五兆円は三百六十五万年。人類の祖先が二足歩行を始めたころから数えて、今日やっと終わります。'),
    (49,   9,   '国の借金、千三百二十三兆円は、四千二百万年。恐竜が絶滅したあと、まだ猿もいない時代からです。'),
    (58,   9,   '平均年収、四百六十万円は、五十三日。桁が変わると、時間の意味が変わる。あなたの年収は、何日ですか？'),
]

# 字幕用テキスト(画面表示向けの表記)
SUBTITLES_JA = [
    '1秒に1円ずつ数えます。1兆円まで、何年かかると思いますか？',
    'まず1万円。2時間46分40秒。まだ余裕ですね。',
    '100万円。11日と13時間。寝ずに数えて、11日です。',
    '1億円。3年と2ヶ月。数え終わるころには、3つ歳をとっています。',
    '10億円。31年8ヶ月。生まれた瞬間から数え始めて、終わるのは31歳です。',
    '1兆円。3万1,700年。数え始めたのは、縄文時代よりずっと前、旧石器時代です。',
    '国家予算、115兆円は365万年。人類の祖先が二足歩行を始めたころから数えて、今日やっと終わります。',
    '国の借金、1,323兆円は、4,200万年。恐竜が絶滅したあと、まだ猿もいない時代からです。',
    '平均年収、460万円は、53日。桁が変わると、時間の意味が変わる。あなたの年収は、何日ですか？',
]
SUBTITLES_EN = [
    "Let's count one yen per second. How long do you think it takes to reach 1 trillion yen?",
    'First, ¥10,000 (about $65). 2 hours, 46 minutes, 40 seconds. Easy.',
    '¥1,000,000 (about $6,500). 11 days and 13 hours, counting without sleep.',
    '¥100,000,000 (about $650,000). 3 years and 2 months. You are three years older when you finish.',
    '¥1,000,000,000 (about $6.5 million). 31 years and 8 months. Start at birth, finish at 31.',
    '¥1 trillion (about $6.5 billion). 31,700 years. You would have started in the Paleolithic, long before Japan\'s Jomon period.',
    "Japan's national budget, ¥115 trillion. 3.65 million years. Start when our ancestors began walking upright, count nonstop, and finish today.",
    "Japan's national debt, ¥1,323 trillion. 42 million years. Start after the dinosaurs died out, before apes even existed, and never stop.",
    "Japan's average salary, ¥4.6 million, is 53 days. Same currency, but every four digits changes what time means. How many days is your salary?",
]
SRT_JA = os.path.join(HERE, 'output', 'subtitles_ja.srt')
SRT_EN = os.path.join(HERE, 'output', 'subtitles_en.srt')

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
        print('engine: VOICEVOX', name)
        self.credit = 'VOICEVOX:' + name.split('/')[0]
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
        self.credit = 'Open JTalk'
        print('engine: Open JTalk (fallback)')
    def __call__(self, text, speed):
        x, sr = self.tts(text, speed=speed, half_tone=-1.0)
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
for li, (start, dur, text) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.3
    speed = 1.15  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.42)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR))

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
for path, subs in ((SRT_JA, SUBTITLES_JA), (SRT_EN, SUBTITLES_EN)):
    with open(path, 'w', encoding='utf-8') as f:
        for i, ((a, b), t) in enumerate(zip(cues, subs), 1):
            f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
    print('wrote', path)

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    prev = envl[i - 1] if i else 0.0
    envl[i] = max(v, prev * 0.9)       # リリース ≈ 0.5 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.20   # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(HERE, 'output', 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST, '| narration credit:', engine.credit)
