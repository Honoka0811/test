# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX(四国めたん)で合成し、BGM(bgm.py)をダッキングしながらミックスする。
出力: output/narration.wav, output/mix.wav, output/cues.json(字幕焼き込み用), output/subtitles_ja.srt
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 4 = セクシー, 6 = ツンツン)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
TOTAL = 70.0
LEAD = 0.35  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 読み上げ原稿, 字幕)  字幕は | で次の画面、/ で改行  render.html の SCENES と対応
SCRIPT = [
    (0, 6, '空気からパンを作った、と言われる発明。ハーバー・ボッシュ法が、すごすぎるんです。',
           '「空気からパンを作った」と/言われる発明|ハーバー・ボッシュ法が/すごすぎるんです'),
    (6, 9, '千九百年ごろ、作物を育てる窒素肥料は、チリ硝石や鳥のふんのグアノ頼み。このままでは小麦が足りなくなる、と警告されていました。',
           '1900年ごろ、窒素肥料は/チリ硝石や鳥のふんのグアノ頼み|「このままでは/小麦が足りなくなる」と/警告されていました'),
    (15, 9, '実は空気の七十八パーセントは窒素。でも窒素どうしは、さんじゅう結合でガッチリつながっていて、植物はそのままでは使えません。',
            '実は空気の78%は窒素|でも窒素どうしは/三重結合でガッチリ|植物はそのままでは/使えません'),
    (24, 12, '千九百九年、ハーバーは、約二百気圧、約五百度という過酷な条件で、窒素と水素からアンモニアを作ることに成功。それをボッシュが、巨大な工場で量産できるようにしました。',
             '1909年、ハーバーは/約200気圧・約500℃という/過酷な条件で|窒素と水素から/アンモニアを作ることに成功|それをボッシュが/巨大な工場で量産可能に'),
    (36, 12, '安い肥料が世界中に広がり、世界人口は、十六億人から八十億人を超えるまでに。今の人類のおよそ半分は、この方法で作られた肥料に支えられていると言われます。',
             '安い肥料が世界中に広がり|世界人口は16億人から/80億人超えに|今の人類のおよそ半分は/この方法の肥料に/支えられていると言われます'),
    (48, 8, 'あなたの体の窒素も、約半分はこの方法がルーツ。世界のエネルギーの一から二パーセントが、この反応に使われています。',
            'あなたの体の窒素も/約半分はこの方法がルーツ|世界のエネルギーの1〜2%が/この反応に使われています'),
    (56, 8, 'ただし、アンモニアは火薬の原料にもなり、戦争を支えました。ハーバー自身も、毒ガス開発を指揮しています。',
            'ただし、アンモニアは/火薬の原料にもなり/戦争を支えました|ハーバー自身も/毒ガス開発を指揮しています'),
    (64, 6, '人類を養い、戦争も支えた、世界を変えた化学反応なんです。',
            '人類を養い、戦争も支えた|世界を変えた化学反応/なんです'),
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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def main():
    engine = VoicevoxEngine()
    def synth(text, speed):
        x, sr = engine(text, speed)
        x = resample(x, sr)
        idx = np.where(np.abs(x) > 0.004)[0]
        return x[max(0, idx[0] - 1200): idx[-1] + 2400] if len(idx) else x

    track = np.zeros(int(TOTAL * SR), dtype=np.float32)
    cues = []
    for start, dur, text, sub in SCRIPT:
        limit = dur - LEAD - 0.3
        speed = 1.15
        for _ in range(6):
            x = synth(text, speed); sec = len(x) / SR
            if sec <= limit: break
            speed = min(speed * (sec / limit) * 1.02, 1.45)
        print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
        n = len(x); f = min(600, n // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        s = int((start + LEAD) * SR); e = min(s + n, len(track))
        track[s:e] += x[:e - s]
        cues.append([round(start + LEAD, 3), round(min(start + LEAD + n / SR + 0.25, start + dur), 3), sub])

    track = track / (np.max(np.abs(track)) or 1) * 0.85
    def write(path, x):
        with wave.open(path, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
        print('wrote', path)
    write(os.path.join(OUT, 'narration.wav'), track)
    json.dump(cues, open(os.path.join(OUT, 'cues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    def ts(t):
        return f'{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round((t % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, (a, b, t) in enumerate(cues, 1):
            f.write(f'{i}\n{ts(a)} --> {ts(b)}\n' + t.replace('|', '\n').replace('/', '') + '\n\n')

    # ---------- BGM をダッキングしながらミックス ----------
    import bgm as bgm_mod
    music = bgm_mod.generate(TOTAL)[:len(track)]
    music = np.pad(music, (0, len(track) - len(music)))
    hop = SR // 20
    rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    envl = np.zeros_like(rms)
    for i, v in enumerate(rms):
        envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
    envl = np.pad(np.repeat(envl, hop), (0, len(track) - len(rms) * hop))
    speech = np.clip(envl / 0.12, 0, 1)
    BGM_SILENT, BGM_SPEECH = 0.42, 0.17
    gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
    k = SR // 10
    gain = np.convolve(gain, np.ones(k) / k, mode='same')
    mixed = track + music * gain
    write(os.path.join(OUT, 'mix.wav'), mixed / max(1.0, np.max(np.abs(mixed)) / 0.95))

if __name__ == '__main__':
    main()
