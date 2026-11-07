# -*- coding: utf-8 -*-
"""script.json の各行を VOICEVOX(四国めたん)で合成し、
output/narration.wav と output/timeline.json(シーン/字幕のタイミング)、output/subtitles_ja.srt を書き出す。

使い方:
  python3 narrate.py             # VOICEVOX で合成(必須)
  python3 narrate.py --estimate  # 音声なしで尺だけ見積もる(映像のプレビュー用)
  python3 narrate.py --kana      # 全行の読みを表示(読み間違いの確認用)
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン)
  VOICEVOX_SPEED 話速(既定 1.28)
"""
import sys, os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
ESTIMATE = '--estimate' in sys.argv

FIRST_LEAD = 0.15  # ショートは冒頭の間を極力詰める
SCENE_LEAD = 0.3   # シーン切替から最初の発話まで
LINE_GAP = 0.18    # 行と行の間
SCENE_TAIL = 0.3   # 最後の発話からシーン切替まで
OUTRO_TAIL = 1.2   # 最後の余韻(短くしてループ再生につなげる)

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class Voicevox:
    def __init__(self):
        from voicevox_core import UserDictWord
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile, UserDict
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        ojt = OpenJtalk(_dict_dir())
        # 辞書にない人名・「〇〇家(け)」などの読みを user_dict.json で補う
        ud = UserDict()
        for w in json.load(open(os.path.join(HERE, 'user_dict.json'), encoding='utf-8')):
            ud.add_word(UserDictWord(priority=10, **w))
        ojt.use_user_dict(ud)
        self.synth = Synthesizer(ort, ojt)
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        self.speed = float(os.environ.get('VOICEVOX_SPEED', '1.28'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        if not name.startswith('四国めたん'):
            print('warning: style', self.style, 'is', name)
        print('engine: VOICEVOX', name, 'speed', self.speed)

    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = self.speed
        q.intonation_scale = 1.2   # 少し抑揚を強めて YouTube 向けに聞きやすく
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x

def estimate_seconds(reading):
    # かな混じり文の概算(VOICEVOX 話速 1.15 で 1 文字あたり約 0.15 秒 + 読点ごとの間)
    return 0.15 * len(reading.replace('、', '').replace('。', '')) + 0.12 * reading.count('、')

script = json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))
engine = None if ESTIMATE else Voicevox()

if '--kana' in sys.argv:  # 読みの確認用: 各行の読み(アクセント句 / ' がアクセント核)を表示して終了
    for sc in script['scenes']:
        for j, (_, reading) in enumerate(sc['lines']):
            print(f"{sc['id']}[{j}]", engine.synth.create_audio_query(reading, engine.style).kana)
    sys.exit(0)

clips = []  # (start_sec, samples)
timeline = {'estimated': ESTIMATE, 'scenes': []}
t = 0.0
for si, sc in enumerate(script['scenes']):
    s_start = t
    t += FIRST_LEAD if si == 0 else SCENE_LEAD
    lines = []
    for li, (disp, reading) in enumerate(sc['lines']):
        if li: t += LINE_GAP
        if engine:
            x = engine(reading); d = len(x) / SR
            clips.append((t, x))
        else:
            d = estimate_seconds(reading)
        lines.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': disp})
        t += d
    t += OUTRO_TAIL if sc['type'] == 'outro' else SCENE_TAIL
    t += sc.get('pause', 0)
    timeline['scenes'].append({'id': sc['id'], 'start': round(s_start, 3), 'end': round(t, 3), 'lines': lines})
    print(f"{sc['id']:10s} {s_start:6.1f}s - {t:6.1f}s ({t - s_start:4.1f}s)")
timeline['total'] = round(t, 3)
print(f'total {t:.1f}s', '(estimated)' if ESTIMATE else '')

json.dump(timeline, open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timeline['scenes']:
        for ln in sc['lines']:
            f.write(f"{i}\n{ts(ln['start'])} --> {ts(ln['end'] + 0.2)}\n{ln['text'].replace('【', '').replace('】', '')}\n\n"); i += 1

if engine:
    track = np.zeros(int((t + 0.5) * SR), dtype=np.float32)
    for st, x in clips:
        s = int(st * SR); track[s:s + len(x)] += x[:len(track) - s]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    print('wrote output/narration.wav')
print('wrote output/timeline.json, output/subtitles_ja.srt')
