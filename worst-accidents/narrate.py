# -*- coding: utf-8 -*-
"""シーンごとのナレーション(VOICEVOX:青山龍星)を合成し、BGM「G線上のアリア」をダッキングしながらミックスして動画に合成する。
voicevox_core が無い場合は Open JTalk にフォールバックする。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'worst_accidents.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'worst_accidents_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')
BGM_FILE = os.path.join(HERE, 'assets', 'air_on_g_string_usaf_band.ogg')
BGM_OFFSET = 4.0   # 音源冒頭の無音を飛ばす

SR = 48000
TOTAL = 87.5
LEAD = 0.5  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応。読み間違い防止のため数字は漢数字
SCRIPT = [
    (0, 6, '人類の歴史に刻まれた、最悪の事故。七つの悲劇を、年代順にたどります。'),
    (6, 10.5, '千九百十二年、タイタニック号。氷山に衝突して沈没し、約千五百人が死亡。救命ボートは、乗船者の半分ほどしかありませんでした。'),
    (16.5, 10.5, '千九百十七年、カナダのハリファックス。弾薬を満載した貨物船が衝突し、大爆発。約二千人が死亡し、九千人が負傷しました。'),
    (27, 10.5, '千九百七十七年、テネリフェ空港。濃い霧の滑走路で、ジャンボ機二機が衝突。五百八十三人が死亡した、航空史上最悪の事故です。'),
    (37.5, 10.5, '千九百八十四年、インドのボパール。農薬工場から猛毒のガスが漏れ、眠る街を襲いました。死者は、一万人を超えるとされます。'),
    (48, 10.5, '千九百八十五年、日本航空百二十三便。群馬県の山中に墜落し、五百二十人が死亡。単独の航空機として、史上最悪の事故です。'),
    (58.5, 10.5, '千九百八十六年、チェルノブイリ原発。原子炉が爆発し、放射性物質が広い範囲に拡散。約三十五万人が、故郷を追われました。'),
    (69, 10.5, '千九百八十七年、フィリピンのドニャ・パス号。定員を大きく超えて航行中、タンカーと衝突し炎上。四千人以上が死亡したとされます。'),
    (79.5, 8, '事故のたびに、安全のルールは見直されてきました。いまの安全は、多くの犠牲の上にあります。'),
]

SUBTITLES = [
    '人類の歴史に刻まれた、最悪の事故。7つの悲劇を、年代順にたどります。',
    '1912年、タイタニック号。氷山に衝突して沈没し、約1,500人が死亡。救命ボートは、乗船者の半分ほどしかありませんでした。',
    '1917年、カナダのハリファックス。弾薬を満載した貨物船が衝突し、大爆発。約2,000人が死亡し、9,000人が負傷しました。',
    '1977年、テネリフェ空港。濃い霧の滑走路で、ジャンボ機2機が衝突。583人が死亡した、航空史上最悪の事故です。',
    '1984年、インドのボパール。農薬工場から猛毒のガスが漏れ、眠る街を襲いました。死者は、1万人を超えるとされます。',
    '1985年、日本航空123便。群馬県の山中に墜落し、520人が死亡。単独の航空機として、史上最悪の事故です。',
    '1986年、チェルノブイリ原発。原子炉が爆発し、放射性物質が広い範囲に拡散。約35万人が、故郷を追われました。',
    '1987年、フィリピンのドニャ・パス号。定員を大きく超えて航行中、タンカーと衝突し炎上。4,000人以上が死亡したとされます。',
    '事故のたびに、安全のルールは見直されてきました。いまの安全は、多くの犠牲の上にあります。',
]
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    pyopenjtalk.g2p('あ')  # 辞書が未ダウンロードなら、ここで取得させる
    return pyopenjtalk.OPEN_JTALK_DICT_DIR.decode() if isinstance(pyopenjtalk.OPEN_JTALK_DICT_DIR, bytes) else str(pyopenjtalk.OPEN_JTALK_DICT_DIR)

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
    # 青山龍星以外の声で黙って書き出さないよう、フォールバックは明示的に許可したときだけ
    if os.environ.get('ALLOW_FALLBACK') != '1':
        sys.exit(f'VOICEVOX を起動できません: {e}\n(Open JTalk で作る場合は ALLOW_FALLBACK=1 を指定)')
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
    speed = 1.1  # 基準速度(重いテーマなので落ち着いたペース)(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.35)
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

# ---------- BGM(G線上のアリア)をダッキングしながらミックス ----------
dec = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', str(BGM_OFFSET), '-i', BGM_FILE, '-t', str(TOTAL),
                      '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], check=True, capture_output=True).stdout
music = np.frombuffer(dec, dtype=np.int16).astype(np.float32) / 32768.0
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
music = music / (np.sqrt(np.mean(music ** 2)) + 1e-9) * 0.10       # 音源の音量を揃える(RMS 約 -20 dBFS)
fo = int(3.0 * SR); music[-fo:] *= np.linspace(1, 0, fo) ** 2         # 終わりは 3 秒でフェードアウト
fi = int(0.8 * SR); music[:fi] *= np.linspace(0, 1, fi)
# ナレーションの包絡(50ms RMS → アタック速く・リリース 0.5 秒で平滑化)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    prev = envl[i - 1] if i else 0.0
    envl[i] = max(v, prev * 0.9)       # リリース ≈ 0.5 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.75, 0.30   # 無音時 / 発話時の BGM ゲイン(線形)
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
