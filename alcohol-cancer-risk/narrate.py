# -*- coding: utf-8 -*-
"""シーンごとのナレーションを合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
既定は VOICEVOX(青山龍星)。voicevox_core が無い場合は Open JTalk にフォールバックする。
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
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'alcohol_cancer_risk.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'alcohol_cancer_risk_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 76.5
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
SCRIPT = [
    (0, 6.5, '毎日のお酒は、がんのリスクをどれだけ上げるのか。数字で見ていきます。'),
    (6.5, 9.5, 'WHOはアルコールを、たばこと同じ、発がん性が確実なグループ1に分類。世界のがんの四パーセントは、お酒が原因と推計されています。'),
    (16, 8.5, '飲酒で増えることが確実ながんは七つ。口、のど、喉頭、食道、肝臓、大腸、そして女性の乳がんです。'),
    (24.5, 8.5, 'ものさしは純アルコール二十グラム。ビール五百ミリリットル、日本酒一合、ワイングラス二杯が、ほぼ二十グラムです。'),
    (33, 14.5, '国立がん研究センターが日本人男性を追跡した研究では、時々飲む人に比べ、一日二合以上でがん全体が一点四倍、三合以上で一点六倍。大腸がんは二合以上で二点一倍、食道がんは四点六倍でした。'),
    (47.5, 10.5, 'では少量なら安全か。一日一杯を十年続けるだけでも、がんのリスクは約五パーセント上昇。WHOも、安全な飲酒量はないと警告しています。'),
    (58, 12, '厚生労働省のガイドラインでは、男性は一日四十グラム、女性は二十グラム以上でリスクが高まるとしています。大腸がんは二十グラム、乳がんは十四グラムから上がります。'),
    (70, 6.5, '飲むなら少なく、休肝日を。リスクを知って、選びましょう。'),
]

# 字幕用テキスト(読み上げ用の漢数字ではなく、画面表示向けの表記)
SUBTITLES = [
    '毎日のお酒は、がんのリスクをどれだけ上げるのか。数字で見ていきます。',
    'WHOはアルコールを、たばこと同じ、発がん性が確実なグループ1に分類。世界のがんの4%は、お酒が原因と推計されています。',
    '飲酒で増えることが確実ながんは7つ。口、のど、喉頭、食道、肝臓、大腸、そして女性の乳がんです。',
    'ものさしは純アルコール20g。ビール500ml、日本酒1合、ワイングラス2杯が、ほぼ20gです。',
    '国立がん研究センターが日本人男性を追跡した研究では、時々飲む人に比べ、1日2合以上でがん全体が1.4倍、3合以上で1.6倍。大腸がんは2合以上で2.1倍、食道がんは4.6倍でした。',
    'では少量なら安全か。1日1杯を10年続けるだけでも、がんのリスクは約5%上昇。WHOも、安全な飲酒量はないと警告しています。',
    '厚生労働省のガイドラインでは、男性は1日40g、女性は20g以上でリスクが高まるとしています。大腸がんは20g、乳がんは14gから上がります。',
    '飲むなら少なく、休肝日を。リスクを知って、選びましょう。',
]
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

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
        self.credit = 'VOICEVOX'
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
        self.credit = 'Open JTalk'
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
for li, (start, dur, text) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.35
    speed = 1.15  # 基準速度(全シーンでペースを揃える)
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
BGM_SILENT, BGM_SPEECH = 0.40, 0.18   # 無音時 / 発話時の BGM ゲイン(線形)
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
print('wrote', DST, '(engine:', engine.credit + ')')
