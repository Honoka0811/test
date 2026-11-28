# -*- coding: utf-8 -*-
"""掛け合いナレーション(ずんだもん × 四国めたん)を VOICEVOX で合成し、
音声の実際の長さから動画のタイムラインを組み立てる。

出力:
  output/voice.wav     … ナレーションのみ(48kHz mono)
  output/subtitles_ja.srt
  timeline.json / timeline.js … render.html と audio.py が読むタイミング情報

使い方: python3 voice.py
環境変数(VOICEVOX CORE の場所。README 参照):
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm にずんだもん・四国めたんが入っている)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk のもの)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000

# 話者: Z = ずんだもん(ノーマル 3)  M = 四国めたん(ノーマル 2)
VOICES = {
    'Z': dict(style=3, speed=1.3, pitch=0.0, intonation=1.25),
    'M': dict(style=2, speed=1.25, pitch=0.0, intonation=1.2),
}

# ---------------------------------------------------------------------------
# 台本。各行 = (話者, 読み上げ用テキスト, 字幕テキスト, マーク)
#   マーク 'p0@0.5' = この行の 50% の時点で perk0 を出す(@ 省略で行頭)
#   pre  = シーン開始から最初のセリフまでの間(ワイプや効果音のぶん)
#   gap  = セリフ間の間 / post = 最後のセリフ後の余韻
# ---------------------------------------------------------------------------
SCENES = [
    dict(id='intro', pre=0.15, gap=0.1, post=0.3, lines=[
        ('M', 'ねえ、楽しいバイトって、どれかしら？', 'ねえ、楽しいバイトって、どれかしら？', []),
        ('Z', 'やってみたくなるバイト、トップファイブを発表するのだ！', 'やってみたくなるバイト TOP5を発表するのだ！', ['top5@0.45']),
    ]),
    dict(id='r5', pre=0.4, gap=0.1, post=0.3, lines=[
        ('Z', '第五位、映画館スタッフ！', '第5位、映画館スタッフ！', ['name@0.38', 'meters@0.9']),
        ('Z', '劇場によっては、映画をタダで観られる特典があるのだ！', '劇場によっては、映画をタダで観られる特典があるのだ！', ['p0@0.15']),
        ('M', '映画好きには、たまらないわね！', '映画好きには、たまらないわね！', ['p1@0', 'p2@0.6']),
    ]),
    dict(id='r4', pre=0.4, gap=0.1, post=0.3, lines=[
        ('Z', '第四位、カフェスタッフ！', '第4位、カフェスタッフ！', ['name@0.38', 'meters@0.9']),
        ('Z', 'ラテアートが上手くなるし、ドリンクの割引があるお店も多いのだ！', 'ラテアートが上手くなるし、ドリンクの割引があるお店も多いのだ！', ['p0@0.05', 'p1@0.5']),
        ('M', 'おしゃれな空間で働けるのも、素敵ね！', 'おしゃれな空間で働けるのも、素敵ね！', ['p2@0.1']),
    ]),
    dict(id='r3', pre=0.4, gap=0.1, post=0.3, lines=[
        ('Z', '第三位、イベント、ライブスタッフ！', '第3位、イベント・ライブスタッフ！', ['name@0.3', 'meters@0.9']),
        ('Z', '一日だけの単発でもオッケー！フェスの熱気を、裏側から味わえるのだ！', '1日だけの単発でもOK！フェスの熱気を、裏側から味わえるのだ！', ['p0@0.05', 'p1@0.45']),
        ('M', 'ひばらいの求人もあるのね！', '日払いの求人もあるのね！', ['p2@0.1']),
    ]),
    dict(id='r2', pre=0.4, gap=0.1, post=0.3, lines=[
        ('Z', '第二位、テーマパークスタッフ！', '第2位、テーマパークスタッフ！', ['name@0.33', 'meters@0.9']),
        ('Z', '毎日がお祭り気分！お客さんの笑顔を、一番近くで見られるのだ！', '毎日がお祭り気分！お客さんの笑顔を、一番近くで見られるのだ！', ['p0@0.05', 'p1@0.4']),
        ('M', 'パークの利用特典がもらえるところも、あるみたいね！', 'パークの利用特典がもらえる所も、あるみたいね！', ['p2@0.1']),
    ]),
    # 第1位の前のドラムロール(暗転+スポットライト)
    dict(id='drum', pre=0.3, gap=0.1, post=1.5, lines=[
        ('M', 'いよいよ、第一位ね……！', 'いよいよ、第1位ね……！', []),
    ]),
    dict(id='r1', pre=0.25, gap=0.12, post=0.4, lines=[
        ('Z', '第一位は、リゾートバイトなのだ！', '第1位は、リゾートバイトなのだ！', ['name@0', 'meters@0.95']),
        ('M', '観光地で、住み込みで働くお仕事ね！', '観光地で、住み込みで働くお仕事ね！', ['what@0.05']),
        ('Z', '寮費や光熱費が無料の求人も多くて、お金がどんどん貯まるのだ！', '寮費や光熱費が無料の求人も多くて、お金がどんどん貯まるのだ！', ['p0@0.05', 'p1@0.5', 'money@0.62']),
        ('M', '休みの日は、温泉や海も楽しめるのね！', '休みの日は、温泉や海も楽しめるのね！', ['p2@0.05']),
        ('Z', '全国から来た仲間もできるのだ！', '全国から来た仲間もできるのだ！', ['p3@0.05']),
    ]),
    dict(id='outro', pre=0.4, gap=0.1, post=2.0, lines=[
        ('M', 'ぜんぶ、やってみたくなっちゃった！', 'ぜんぶ、やってみたくなっちゃった！', []),
        ('Z', '気になったバイト、コメントで教えてほしいのだ！', '気になったバイト、コメントで教えてほしいのだ！', ['cta@0.3']),
    ]),
]


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d:
        return d
    import pyopenjtalk
    p = pyopenjtalk.OPEN_JTALK_DICT_DIR
    return p.decode() if isinstance(p, bytes) else p


class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get(
            'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        names = {st.id: f'{c.name}/{st.name}' for c in self.synth.metas() for st in c.styles}
        for k, v in VOICES.items():
            print(f'voice {k}: VOICEVOX {names[v["style"]]}')

    def __call__(self, text, v):
        q = self.synth.create_audio_query(text, v['style'])
        q.speed_scale = v['speed']
        q.pitch_scale = v['pitch']
        q.intonation_scale = v['intonation']
        q.pre_phoneme_length = 0.04
        q.post_phoneme_length = 0.08
        wav = self.synth.synthesis(q, v['style'])
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        # 前後の無音を詰める
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 600): idx[-1] + 1800]
        f = min(400, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
        return x


def main():
    os.makedirs(OUT, exist_ok=True)
    tts = Voicevox()
    clips, scenes, lines = [], [], []
    t = 0.0
    for sc in SCENES:
        s0 = t
        t += sc['pre']
        marks = {}
        for li, (spk, say, sub, mk) in enumerate(sc['lines']):
            if li:
                t += sc['gap']
            x = tts(say, VOICES[spk])
            d = len(x) / SR
            clips.append((t, x))
            for m in mk:
                name, _, frac = m.partition('@')
                marks[name] = round(t + d * float(frac or 0), 3)
            lines.append(dict(spk=spk, text=sub, t0=round(t, 3), t1=round(t + d, 3), scene=sc['id']))
            print(f'{t:6.2f}s  {spk}  {d:4.2f}s  {sub}')
            t += d
        t += sc['post']
        scenes.append(dict(id=sc['id'], t0=round(s0, 3), t1=round(t, 3), marks=marks))
    total = round(t, 3)

    track = np.zeros(int(np.ceil(total * SR)) + SR, dtype=np.float32)
    for st, x in clips:
        s = int(st * SR)
        track[s:s + len(x)] += x
    track = track[:int(total * SR)]
    track *= 0.85 / (np.max(np.abs(track)) or 1)
    with wave.open(os.path.join(OUT, 'voice.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    tl = dict(duration=total, fps=30, scenes=scenes, lines=lines)
    with open(os.path.join(HERE, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('// voice.py が自動生成(手で編集しない)\nwindow.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')

    def ts(x):
        ms = int(round(x * 1000))
        return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, ln in enumerate(lines, 1):
            who = 'ずんだもん' if ln['spk'] == 'Z' else '四国めたん'
            end = min(ln['t1'] + 0.25, total, lines[i]['t0'] - 0.02 if i < len(lines) else total)
            f.write(f"{i}\n{ts(ln['t0'])} --> {ts(end)}\n{who}:{ln['text']}\n\n")
    print(f'total {total:.2f}s  → voice.wav / timeline.js / subtitles_ja.srt')


if __name__ == '__main__':
    main()
