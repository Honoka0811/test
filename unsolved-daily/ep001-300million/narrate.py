# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'unsolved_001_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'unsolved_001_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

SR = 48000
TOTAL = 58.0
LEAD = 0.25  # キュー開始からナレーション開始までの間

# (開始秒, 枠の長さ, 読み上げ原稿)  script.md と対応
SCRIPT = [
    (0.0,  3.2, 'たった三分で、三億円が消えました。'),
    (3.2,  2.8, '犯人は、今も捕まっていません。'),
    (6.0,  5.0, '千九百六十八年、十二月十日。雨の朝の、東京、府中。'),
    (11.0, 4.0, '現金三億円を積んだ、銀行の車が走っていました。'),
    (15.0, 3.2, '突然、白バイの警察官が車を止めます。'),
    (18.2, 3.6, 'この車に、爆弾が仕掛けられている。'),
    (22.0, 5.2, '行員が車を離れた隙に、男は車ごと三億円を奪って消えました。'),
    (27.2, 3.8, 'かかった時間は、わずか三分。けが人はゼロです。'),
    (31.0, 4.6, '警察はのべ十七万人を投入。遺留品は、百二十点以上。'),
    (35.6, 3.4, 'それでも、犯人にはたどり着けませんでした。'),
    (39.0, 6.2, 'しかもあの有名なモンタージュ写真は、事件と無関係な人の顔から作られていました。'),
    (45.2, 3.3, 'そして千九百七十五年、時効が成立。'),
    (48.5, 4.0, '犯人は今も、どこかで普通に暮らしているのかもしれません。'),
    (52.5, 5.3, 'あなたの推理を、コメントで教えて。フォローで、明日の事件もお見逃しなく。'),
]

# 字幕用テキスト(画面表示向けの表記)
SUBTITLES = [
    'たった3分で、3億円が消えました。',
    '犯人は、今も捕まっていません。',
    '1968年12月10日、雨の朝。東京・府中。',
    '現金3億円を積んだ、銀行の車が走っていました。',
    '突然、白バイの警察官が車を止めます。',
    '「この車に、爆弾が仕掛けられている」',
    '行員が車を離れた隙に、男は車ごと3億円を奪って消えました。',
    'かかった時間は、わずか3分。けが人はゼロ。',
    '警察はのべ17万人を投入。遺留品は120点以上。',
    'それでも、犯人にはたどり着けませんでした。',
    'しかもあの有名なモンタージュ写真は、事件と無関係な人の顔から作られていました。',
    'そして1975年、時効が成立。',
    '犯人は今も、どこかで普通に暮らしているのかもしれません。',
    'あなたの推理をコメントで。フォローで明日の事件も。',
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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))  # 2 = 四国めたん ノーマル
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
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
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for li, (start, dur, text) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.2
    speed = 1.12  # 基準速度(テンポ感を出しつつ聞き取れる速さ)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.35)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR, SUBTITLES[li]))

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
os.makedirs(os.path.join(HERE, 'output'), exist_ok=True)
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(SRT, 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
print('wrote', SRT)

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
BGM_SILENT, BGM_SPEECH = 0.42, 0.17   # 無音時 / 発話時の BGM ゲイン(線形)
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
print('wrote', DST)
