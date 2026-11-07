# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、字幕のパート単位のタイミング(timeline)を書き出す。

VOICEVOX の AudioQuery に含まれるモーラ長から、各字幕パートが「実際に発話される時刻」を求め、
render.html の字幕演出(発話中のパートを強調)と SRT に使う。

使い方: python3 narrate.py
出力:   output/narration.wav  output/timeline.json  output/timeline.js  output/subtitles_ja.srt
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが入っている)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 あまあま / 6 ツンツン / 4 セクシー)
  VOICEVOX_SPEED 話速(既定 1.1)
"""
import sys, os, io, wave, glob, json, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)

SR = 48000
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.18'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))

# ---------------------------------------------------------------------------
# 台本。シーン → 行 → パート。パートは「読み上げ文字列」か (読み上げ, 表示) のタプル。
# 行の間は GAP_LINE 秒、シーンの間は GAP_SCENE 秒あける。シーンごとに pre(頭の余白)を指定できる。
# ---------------------------------------------------------------------------
GAP_LINE = 0.18
GAP_SCENE = 0.45
SCRIPT = [
    dict(id='hook', pre=0.35, lines=[
        ['逆境で、', '折れる人と', '強くなる人。'],
        ['その差は、', 'たった一つです。'],
    ]),
    dict(id='pain', pre=0.5, lines=[
        ['頑張っても、', '報われない。'],
        ['信じてた人に、', '裏切られる。'],
        ['夜、', '「なんで自分だけ」って', '思ったこと、', 'ありませんか。'],
    ]),
    dict(id='bamboo', pre=0.45, lines=[
        ['でも、', '知ってほしい。'],
        ['竹は、', '芽を出すまでの数年間、', '地下で根だけを', '伸ばします。'],
        ['そして', '芽を出した瞬間、', ('一日で一メートル', '1日で1メートル'), '伸びる。'],
    ]),
    dict(id='reject', pre=0.45, lines=[
        ['ハリー・ポッターの原稿は、', ('十二の出版社に', '12の出版社に'), '断られました。'],
        ['一度でも', '諦めていたら、', 'あの物語は', '存在しなかった。'],
    ]),
    dict(id='core', pre=0.5, lines=[
        ['逆境は、', 'あなたを壊すために', 'あるんじゃない。'],
        ['あなたが何者かを、', '教えるためにある。'],
        ['折れる人と', '強くなる人の差は、', 'たった一つ。'],
        ['今を', '「終わり」だと思うか、', '「根を張る時間」だと', '思うか。'],
    ]),
    dict(id='close', pre=0.5, lines=[
        ['だから今日も、', 'あと一歩だけ。'],
        ['芽が出る日は、', '必ず来る。'],
    ]),
    dict(id='cta', pre=0.45, lines=[
        ['今、', '逆境の中にいる人は、', 'コメントに', '「根を張る」と', '書いてください。'],
        [('一年後、', '1年後、'), '報告しに来てね。'],
    ]),
]

# ---------------------------------------------------------------------------
def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == STYLE)
        print('engine: VOICEVOX', self.name)

    def __call__(self, text, speed):
        """音声(48kHz float32)と、各モーラの開始時刻リストを返す"""
        q = self.synth.create_audio_query(text, STYLE)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.08
        q.post_phoneme_length = 0.12
        q.intonation_scale = 1.15   # 抑揚を少し強めに
        # モーラごとの開始時刻
        t = q.pre_phoneme_length / speed
        mora_t = []
        for ap in q.accent_phrases:
            for m in ap.moras:
                mora_t.append(t)
                t += ((m.consonant_length or 0) + m.vowel_length) / speed
            p = ap.pause_mora
            if p is not None:
                plen = p['vowel_length'] if isinstance(p, dict) else p.vowel_length
                t += plen / speed
        wav = self.synth.synthesis(q, STYLE)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        return x, mora_t, t

SMALL = set('ァィゥェォャュョヮ')
def mora_count(text):
    import pyopenjtalk
    kana = pyopenjtalk.g2p(text, kana=True)
    return sum(1 for ch in kana if ('ァ' <= ch <= 'ヺ' or ch == 'ー') and ch not in SMALL)

engine = Voicevox()

track = []
cursor = 0.0
timeline = []
srt = []
for sc in SCRIPT:
    cursor += GAP_SCENE if timeline else 0
    scene = dict(id=sc['id'], start=round(cursor, 3), lines=[])
    cursor += sc.get('pre', 0.4)
    for parts in sc['lines']:
        parts = [(p, p) if isinstance(p, str) else p for p in parts]
        spoken = ''.join(p[0] for p in parts)
        x, mora_t, end_t = engine(spoken, SPEED)
        # パートの開始時刻: 各パートのモーラ数を累積して mora_t を引く
        counts = [mora_count(p[0]) for p in parts]
        total = sum(counts)
        if total != len(mora_t):
            # 読み分けの差で合わない場合は比例配分で補正
            scale = len(mora_t) / max(total, 1)
            counts = [c * scale for c in counts]
        idx = 0.0
        pstarts = []
        for c in counts:
            i = min(int(round(idx)), len(mora_t) - 1)
            pstarts.append(mora_t[i])
            idx += c
        speech_end = end_t  # post_phoneme 含む
        line = dict(start=round(cursor, 3), end=round(cursor + speech_end, 3), spoken=spoken,
                    display=''.join(p[1] for p in parts),
                    parts=[dict(text=p[1], start=round(cursor + s, 3)) for p, s in zip(parts, pstarts)])
        scene['lines'].append(line)
        srt.append((line['start'], line['end'], line['display']))
        # フェード処理して配置
        n = len(x); f = min(480, n // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        track.append((cursor, x))
        print(f"{cursor:6.2f}s +{len(x)/SR:4.2f}s  {spoken}")
        cursor += len(x) / SR + GAP_LINE
    scene['end'] = round(cursor - GAP_LINE, 3)
    timeline.append(scene)

TOTAL = round(cursor + 1.6, 2)   # 末尾の余白
buf = np.zeros(int(TOTAL * SR), dtype=np.float32)
for s, x in track:
    i = int(s * SR); buf[i:i + len(x)] += x
buf /= max(1e-6, np.max(np.abs(buf))) / 0.85

WAV = os.path.join(OUT, 'narration.wav')
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())

data = dict(total=TOTAL, fps=30, speaker=engine.name, scenes=timeline)
with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps(data, ensure_ascii=False) + ';\n')

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(srt, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.25, TOTAL))}\n{t}\n\n')
print(f'wrote {WAV}  total={TOTAL}s  scenes=' + ', '.join(f"{s['id']}@{s['start']}" for s in timeline))
