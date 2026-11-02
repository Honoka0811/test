# -*- coding: utf-8 -*-
"""シーンごとのナレーション(男性音声)を合成し、動画に合成する。
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
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'pacific_war_power_gap.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'pacific_war_power_gap_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 71.5
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
SCRIPT = [
    (0, 8.5, '千九百四十一年十二月、日本は米国との戦争に踏み切りました。終戦までの四年間で、日米の戦力差はどう変わったのか。'),
    (8.5, 8.5, '開戦時の国力を比べると、GDPは米国が日本の約五点六倍、鉄鋼は約十一倍、石油はおよそ五百四十倍でした。'),
    (17, 8.5, 'しかし空母では日本が優位でした。日本の十隻に対し、米国は太平洋にわずか三隻。この差が緒戦の快進撃を支えます。'),
    (25.5, 12, '航空機の生産数です。千九百四十三年、米国は年間八万六千機を生産し、差は決定的になります。四年間の累計は、日本七万機に対し米国三十一万機でした。'),
    (37.5, 12, '空母の保有数です。ミッドウェーで主力四隻を失った日本は損失を埋められず、千九百四十三年に米国が逆転。千九百四十五年には、日本の稼働空母はほぼゼロになります。'),
    (49.5, 9, '日本の商船は、米潜水艦の攻撃で六百四十万トンから百五十万トンへ激減。石油の備蓄も枯渇し、艦隊は動けなくなります。'),
    (58.5, 8.5, '量の差は質の差へ。新人搭乗員の飛行時間は七百時間から百時間未満に落ち、マリアナ沖海戦では約三百機を失いました。'),
    (67, 4.5, '緒戦の優位は、国力の差を覆せませんでした。'),
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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
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
for start, dur, text in SCRIPT:
    limit = dur - LEAD - 0.35
    speed = 1.2  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.3)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    # フェードイン/アウト
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', WAV,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
