# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん、ノーマル/ささやき/ヒソヒソ混在)を合成し、
BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(ささやき系は 0.vvm に加えて 4〜8.vvm が必要)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'unsolved_002_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'unsolved_002_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

SR = 48000
TOTAL = 58.0
LEAD = 0.25

NORMAL, SASAYAKI, HISOHISO = 2, 36, 37   # 四国めたんのスタイルID

# (開始秒, 枠の長さ, スタイル, 読み上げ原稿)  script.md と対応
SCRIPT = [
    (0.0,  3.6, SASAYAKI, '雪の足跡は、森から家へ続いていました。'),
    (3.6,  3.4, HISOHISO, 'でも、出た足跡は、どこにもない。'),
    (7.0,  3.8, NORMAL,   '百年前のドイツ、ヒンターカイフェック農場。'),
    (10.8, 3.2, NORMAL,   'ここで一家六人が殺されました。'),
    (14.0, 3.4, NORMAL,   '異変は、数日前から始まっていました。'),
    (17.4, 2.8, SASAYAKI, '屋根裏から、足音がする。'),
    (20.2, 2.8, NORMAL,   '鍵が消え、見知らぬ新聞が増える。'),
    (23.0, 5.0, NORMAL,   '三月三十一日の夜。家族は一人ずつ納屋へ呼ばれ、戻りませんでした。'),
    (28.0, 3.0, NORMAL,   'それでも、事件は終わりません。'),
    (31.0, 3.0, HISOHISO, '犯人は、逃げなかったんです。'),
    (34.0, 5.6, NORMAL,   '数日間この家に住み、家畜に餌をやり、煙突からは煙が上がっていました。'),
    (40.0, 4.2, NORMAL,   '容疑者は百人以上。それでも犯人は分からないまま。'),
    (44.2, 3.8, NORMAL,   '翌年、家は取り壊されました。'),
    (48.5, 3.6, SASAYAKI, '屋根裏の足音の主は、誰だったんでしょうね。'),
    (52.5, 5.0, NORMAL,   'あなたの考えをコメントで。フォローで、明日の不気味な事件もお見逃しなく。'),
]

SUBTITLES = [
    '雪の足跡は、森から家へ続いていた',
    'でも、家から出た足跡は、どこにもない',
    '100年前のドイツ、ヒンターカイフェック農場。',
    'ここで一家6人が殺された。',
    '異変は、数日前から始まっていた。',
    '屋根裏から、足音がする……',
    '鍵が消え、見知らぬ新聞が増える。',
    '3月31日の夜、家族は納屋へ一人ずつ呼び出されて、戻らなかった。',
    'それでも、事件は終わらない。',
    '犯人は、逃げなかった。',
    '数日間この家に住み、家畜に餌をやり、煙突からは煙が上がっていた。',
    '容疑者は100人以上。それでも犯人は分からないまま。',
    '翌年、家は取り壊された。',
    '屋根裏の足音の主は、誰だったのか。',
    'あなたの考えをコメントで。フォローで明日の事件も。',
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
        have = {st.id for c in self.synth.metas() for st in c.styles}
        need = {s for (_, _, s, _) in SCRIPT}
        missing = need - have
        if missing:
            raise RuntimeError(f'styles {missing} not found in loaded vvms')
        print('engine: VOICEVOX 四国めたん (styles:', sorted(need), ')')
    def __call__(self, text, style, speed):
        q = self.synth.create_audio_query(text, style)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        if style == NORMAL:
            q.pitch_scale = -0.02   # 少し低く、暗いトーンに
        wav = self.synth.synthesis(q, style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback / スタイルなし)')
    def __call__(self, text, style, speed):
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

def synth(text, style, speed):
    x, sr = engine(text, style, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
TARGET_RMS = 0.085   # 行ごとにラウドネスをそろえる(ささやきが埋もれないように)
for li, (start, dur, style, text) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.2
    speed = 1.0 if style != NORMAL else 1.05   # ささやきはゆっくり
    for _ in range(6):
        x = synth(text, style, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.35)
    # 行ごとのRMS正規化(ゲインは最大6倍までに制限)
    rms = float(np.sqrt(np.mean(x ** 2))) or 1e-6
    g = min(6.0, TARGET_RMS / rms)
    x = x * g
    pk = float(np.max(np.abs(x)))
    if pk > 0.95: x *= 0.95 / pk
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  style={style:2d} speed={speed:.2f} gain={g:.2f}  {text[:16]}…')
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
    envl[i] = max(v, prev * 0.9)
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.40, 0.14   # ささやきが埋もれないよう発話時はやや深めに下げる
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
