# -*- coding: utf-8 -*-
"""シーンごとのナレーション(VOICEVOX: 四国めたん)を合成し、BGM(bgm.mjs で生成した output/bgm.wav)をダッキングしながらミックスして動画に合成する。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'sixties_checklist_silent.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'sixties_checklist.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')
MIX = os.path.join(HERE, 'output', 'mix.wav')

SR = 48000
TITLE_DUR, ITEM_DUR, END_DUR = 4.6, 5.6, 6.0   # render.html と同じ
LEAD = 0.35                                     # シーン開始からナレーション開始までの間

# (原稿(読み上げ用), 字幕用テキスト)  順にタイトル → 10 項目 → 締め
LINES = [
    ('六十代のうちに、やっておきたいこと、じっせん!',
     '60代のうちにやっておきたいこと10選!'),
    ('その一、体のメンテナンス。健診は毎年、歯科検診は半年ごとに。',
     'その1、体のメンテナンス。健診は毎年、歯科検診は半年ごとに。'),
    ('その二、筋肉貯金。一日二十分の散歩が、十年後の足腰を守ります。',
     'その2、筋肉貯金。1日20分の散歩が、10年後の足腰を守ります。'),
    ('その三、お金の棚卸し。年金と資産を把握して、安心の家計プランを。',
     'その3、お金の棚卸し。年金と資産を把握して、安心の家計プランを。'),
    ('その四、持ち物を減らす。元気なうちに整理すると、暮らしが軽くなります。',
     'その4、持ち物を減らす。元気なうちに整理すると、暮らしが軽くなります。'),
    ('その五、エンディングノート。もしもの時の希望を書いて、家族と共有を。',
     'その5、エンディングノート。もしもの時の希望を書いて、家族と共有を。'),
    ('その六、行きたい場所へ旅に出る。動ける今が、いちばんの旅行シーズン。',
     'その6、行きたい場所へ旅に出る。動ける今が、いちばんの旅行シーズン。'),
    ('その七、新しい趣味や学び。始めるのに、遅すぎることはありません。',
     'その7、新しい趣味や学び。始めるのに、遅すぎることはありません。'),
    ('その八、ひととのつながり。地域や趣味の仲間は、これからの大きな財産です。',
     'その8、人とのつながり。地域や趣味の仲間は、これからの大きな財産です。'),
    ('その九、住まいの見直し。手すりや段差、住み替えも早めに。',
     'その9、住まいの見直し。手すりや段差、住み替えも早めに。'),
    ('その十、大切な人との時間。ありがとうは、言えるうちに伝えましょう。',
     'その10、大切な人との時間。「ありがとう」は、言えるうちに伝えましょう。'),
    ('全部やらなくて大丈夫。気になった一つから、今日、始めてみませんか?',
     '全部やらなくて大丈夫。気になった1つから、今日、始めてみませんか?'),
]
SCRIPT = [(0.0, TITLE_DUR, LINES[0][0])]
for i in range(10):
    SCRIPT.append((TITLE_DUR + i * ITEM_DUR, ITEM_DUR, LINES[i + 1][0]))
SCRIPT.append((TITLE_DUR + 10 * ITEM_DUR, END_DUR, LINES[11][0]))
TOTAL = TITLE_DUR + 10 * ITEM_DUR + END_DUR

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
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.intonation_scale = 1.15     # 少し抑揚を強めて元気に
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

engine = VoicevoxEngine()

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
    speed = 1.2  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.3)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR, LINES[li][1]))

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

# ---------- BGM をダッキングしながらミックス(ステレオ) ----------
def load_bgm(path):
    with wave.open(path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    x = x.reshape(-1, ch).T
    if ch == 1: x = np.vstack([x, x])
    if sr != SR: x = np.vstack([resample(c, sr) for c in x])
    return x
BGM = os.path.join(HERE, 'output', 'bgm.wav')
if not os.path.exists(BGM):
    subprocess.run(['node', os.path.join(HERE, 'bgm.mjs'), str(TOTAL), BGM], check=True)
music = load_bgm(BGM)                                # (2, n)  bgm.mjs(「春」ポップアレンジ)の出力
music = music[:, :len(track)] if music.shape[1] >= len(track) else np.pad(music, ((0, 0), (0, len(track) - music.shape[1])))
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    prev = envl[i - 1] if i else 0.0
    envl[i] = max(v, prev * 0.9)       # リリース ≈ 0.5 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.55, 0.22   # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = music * gain + track[None, :]
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
with wave.open(MIX, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed.T * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
