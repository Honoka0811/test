# -*- coding: utf-8 -*-
"""シーンごとのナレーション(VOICEVOX:青山龍星)を合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
エンジンの優先順:
  1. VOICEVOX ENGINE (HTTP)  … 環境変数 VOICEVOX_URL(既定 http://localhost:50021)
     例: docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
  2. voicevox_core (Python)  … VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT
  3. Open JTalk               … ALLOW_FALLBACK=1 のときだけ使う(確認用プレビュー。出力名に _preview_openjtalk が付く)
使い方: python3 narrate.py [入力mp4] [出力mp4]
VOICEVOX_STYLE: スタイルID(既定 13 = 青山龍星 ノーマル)
"""
import sys, os, io, wave, glob, json, subprocess, urllib.request, urllib.parse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'air_raids.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'air_raids_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 67
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
SCRIPT = [
    (0, 7, '太平洋戦争末期、日本本土は激しい空襲にさらされました。被害の大きかった空襲を振り返ります。'),
    (7, 10.5, '千九百四十四年十一月、マリアナ諸島からビーニジュウクの本土空襲が本格化。翌年三月からは、夜間に低空から市街地を焼き払う作戦に変わります。'),
    (17.5, 11.5, '千九百四十五年三月十日、東京大空襲。約三百機のビーニジュウクが下町を焼き払い、一夜で約十万人が亡くなりました。焼失家屋は約二十七万戸です。'),
    (29, 10, '空襲は大阪、名古屋、神戸などの大都市に広がり、それぞれの都市で数千人から一万人以上が犠牲になりました。'),
    (39, 9, '六月以降は、地方の中小都市も標的になります。富山では、市街地の約九十九点五パーセントが焼失しました。'),
    (48, 11, 'そして八月、広島と長崎に原子爆弾が投下されます。その年の末までに、二つの都市で合わせて二十万人以上が亡くなりました。'),
    (59, 8, '空襲による死者は、全国で五十万人以上とも言われます。失われた日常を、忘れないために。'),
]

# 字幕用テキスト(画面表示向けの表記)
SUBTITLES = [
    '太平洋戦争末期、日本本土は激しい空襲にさらされました。被害の大きかった空襲を振り返ります。',
    '1944年11月、マリアナ諸島からB-29の本土空襲が本格化。翌年3月からは、夜間に低空から市街地を焼き払う作戦に変わります。',
    '1945年3月10日、東京大空襲。約300機のB-29が下町を焼き払い、一夜で約10万人が亡くなりました。焼失家屋は約27万戸です。',
    '空襲は大阪、名古屋、神戸などの大都市に広がり、それぞれの都市で数千人から1万人以上が犠牲になりました。',
    '6月以降は、地方の中小都市も標的になります。富山では、市街地の約99.5%が焼失しました。',
    'そして8月、広島と長崎に原子爆弾が投下されます。その年の末までに、2つの都市で合わせて20万人以上が亡くなりました。',
    '空襲による死者は、全国で50万人以上とも言われます。失われた日常を、忘れないために。',
]
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxHttpEngine:
    def __init__(self):
        self.url = os.environ.get('VOICEVOX_URL', 'http://localhost:50021').rstrip('/')
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
        speakers = json.load(urllib.request.urlopen(self.url + '/speakers', timeout=5))
        name = next((sp['name'] + '/' + st['name']) for sp in speakers for st in sp['styles'] if st['id'] == self.style)
        print('engine: VOICEVOX ENGINE', name)
    def __call__(self, text, speed):
        qs = urllib.parse.urlencode({'text': text, 'speaker': self.style})
        q = json.load(urllib.request.urlopen(urllib.request.Request(self.url + '/audio_query?' + qs, method='POST')))
        q.update(speedScale=speed, prePhonemeLength=0.05, postPhonemeLength=0.1, outputSamplingRate=SR)
        req = urllib.request.Request(self.url + '/synthesis?speaker=%d' % self.style, data=json.dumps(q).encode(),
                                     headers={'Content-Type': 'application/json'})
        with wave.open(io.BytesIO(urllib.request.urlopen(req).read())) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

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

engine = None
for cls in (VoicevoxHttpEngine, VoicevoxEngine):
    try:
        engine = cls(); break
    except Exception as e:  # noqa
        print(cls.__name__, 'unavailable:', e)
if engine is None:
    if os.environ.get('ALLOW_FALLBACK') != '1':
        sys.exit('VOICEVOX が見つかりません。VOICEVOX ENGINE を起動するか、ALLOW_FALLBACK=1 で Open JTalk プレビューを作成してください。')
    engine = OpenJtalkEngine()
    DST = DST.replace('.mp4', '_preview_openjtalk.mp4')
    WAV = WAV.replace('.wav', '_preview_openjtalk.wav')

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
        speed = min(speed * (sec / limit) * 1.02, 1.3)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    # フェードイン/アウト
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
# ナレーションの包絡(50ms RMS → アタック速く・リリース 0.5 秒で平滑化)
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
# ゲイン変化を 100ms で滑らかに
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
