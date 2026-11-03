# -*- coding: utf-8 -*-
"""シーンごとのナレーション(男性音声)を合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
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
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'scramble_trend.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'scramble_trend_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 85.0
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
SCRIPT = [
    (0, 8.5, '日本の空で、去年一年間に戦闘機が緊急発進した回数は、五百九十五回。一日に一点六回のペースです。'),
    (8.5, 9, 'レーダーが国籍不明機を捉えると、戦闘機が五分以内に離陸し、領空侵犯を防ぐ。これがスクランブルです。'),
    (17.5, 16, '推移を見ると、二千十年度は三百八十六回。中国機の活動が増えた二千十六年度には千百六十八回と、一日三回以上のペースになりました。その後は減り、二千二十五年度は五百九十五回。過去五年で最少です。'),
    (33.5, 10.5, '相手は、中国機が三百六十六回で約六割、ロシア機が二百十四回で約三割六分。中国機のピークは二千十六年度の八百五十一回でした。'),
    (44, 8, '場所は沖縄周辺に集中。那覇を拠点とする南西航空方面隊が三百四十八回、全体の約六割です。'),
    (52, 17, 'なぜ減ったのか。防衛省は明言していませんが、三つの見方があります。中国機の飛行が決まったルートに定型化したこと。ウクライナ侵攻の年に、ロシア機への対応が百五十回まで減ったこと。そして、空自の対応能力が限界に近づいたことです。'),
    (69, 9.5, 'ところが二千二十六年度は一転。上半期だけで四百四十二回、前年同期の約一点七倍に急増。情報収集機の飛行が目立ちます。'),
    (78.5, 6.5, '回数が減っても、脅威が減ったわけではありません。'),
]

# 字幕用テキスト(読み上げ用の漢数字ではなく、画面表示向けの表記)
SUBTITLES = [
    '日本の空で、去年1年間に戦闘機が緊急発進した回数は595回。1日に1.6回のペースです。',
    'レーダーが国籍不明機を捉えると、戦闘機が5分以内に離陸し、領空侵犯を防ぐ。これがスクランブルです。',
    '推移を見ると、2010年度は386回。中国機の活動が増えた2016年度には1,168回と、1日3回以上のペースになりました。その後は減り、2025年度は595回。過去5年で最少です。',
    '相手は、中国機が366回で約6割、ロシア機が214回で約36%。中国機のピークは2016年度の851回でした。',
    '場所は沖縄周辺に集中。那覇を拠点とする南西航空方面隊が348回、全体の約6割です。',
    'なぜ減ったのか。防衛省は明言していませんが、3つの見方があります。中国機の飛行が決まったルートに定型化したこと。ウクライナ侵攻の年に、ロシア機への対応が150回まで減ったこと。そして、空自の対応能力が限界に近づいたことです。',
    'ところが2026年度は一転。上半期だけで442回、前年同期の約1.7倍に急増。情報収集機の飛行が目立ちます。',
    '回数が減っても、脅威が減ったわけではありません。',
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
cues = []
for li, (start, dur, text) in enumerate(SCRIPT):
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
