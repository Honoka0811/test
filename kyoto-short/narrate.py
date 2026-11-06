# -*- coding: utf-8 -*-
"""台本(SCENES)を VOICEVOX:四国めたん で合成し、
  output/narration.wav … ナレーション
  timeline.js         … シーン/字幕のタイミング(render.html が読む)
  output/subtitles_ja.srt
を書き出す。シーンの長さはナレーションの長さから自動で決まる。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
SPEED = 1.18     # ショート向けにテンポ速め
GAP = 0.16       # フレーズ間の間

# (シーンID, 前の間, 後の余白, [(読み上げ, 字幕), ...])
SCENES = [
    ('hook', 0.10, 0.25, [
        ('きよみずの舞台から、本当に飛び降りた人がいるって、知ってた?', '清水の舞台から\n本当に飛び降りた人がいる!?'),
    ]),
    ('title', 0.05, 0.35, [
        ('京都の、ヤバい雑学、ベストスリー!', '京都のヤバい雑学 TOP3'),
    ]),
    ('kiyomizu', 0.30, 0.45, [
        ('第三位、きよみずでら。', '第3位 清水寺'),
        ('江戸時代、ここから飛び降りた記録は、なんと、にひゃくさんじゅうよんけん。', '江戸時代に飛び降りた記録は\nなんと234件'),
        ('しかも、生存率は、約八十五パーセント!', 'しかも生存率は約85%!'),
        ('高さ約十三メートルの舞台は、釘を使わない、かけづくりという工法なんです。', '高さ約13mの舞台は\n釘を使わない「懸造り」'),
    ]),
    ('kinkaku', 0.30, 0.45, [
        ('第二位、金閣寺。', '第2位 金閣寺'),
        ('実は千九百五十年に、放火で全焼しています。', '実は1950年に\n放火で全焼している'),
        ('今の金閣は再建されたもので、貼られた金箔は、約二十万枚!', '今の金閣は再建されたもの\n金箔は約20万枚!'),
    ]),
    ('inari', 0.30, 0.45, [
        ('そして第一位、伏見稲荷大社。', '第1位 伏見稲荷大社'),
        ('千本鳥居って言うけど、実は山全体で、約一万基!', '「千本鳥居」と言うけど\n実は山全体で約1万基!'),
        ('全部まわると、約二時間かかるんです。', '全部まわると約2時間'),
    ]),
    ('outro', 0.30, 0.90, [
        ('行ったことある場所、コメントで教えてね!', '行ったことある場所\nコメントで教えてね!'),
        ('保存して、京都旅行で使ってね!', '保存して京都旅行で使ってね'),
    ]),
]

class Engine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.s = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', '/home/user/vv/open_jtalk_dic_utf_8-1.11')))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.s.load_voice_model(m)
        name = next(c.name + '/' + st.name for c in self.s.metas() for st in c.styles if st.id == STYLE)
        print('engine: VOICEVOX', name)
    def __call__(self, text):
        q = self.s.create_audio_query(text, STYLE)
        q.speed_scale = SPEED
        q.pitch_scale = 0.02          # 少し明るく
        q.intonation_scale = 1.25     # 抑揚を強めに
        q.pre_phoneme_length = 0.02
        q.post_phoneme_length = 0.05
        with wave.open(io.BytesIO(self.s.synthesis(q, STYLE))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        return x[max(0, idx[0] - 600): idx[-1] + 1800] if len(idx) else x

def main():
    eng = Engine()
    clips, scenes, caps = [], [], []
    t = 0.0
    for sid, pre, post, lines in SCENES:
        s0 = t; t += pre
        for say, show in lines:
            x = eng(say)
            n = len(x); f = min(400, n // 4)
            x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
            clips.append((t, x))
            d = n / SR
            caps.append({'t0': round(t, 3), 't1': round(t + d, 3), 'text': show, 'scene': sid})
            print(f'{t:6.2f}s {d:4.2f}s {show.replace(chr(10), " ")}')
            t += d + GAP
        t += post - GAP
        scenes.append({'id': sid, 't0': round(s0, 3), 't1': round(t, 3)})
    total = round(t, 3)
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, x in clips:
        s = int(st * SR); track[s:s + len(x)] += x
    track = track[:int(total * SR)]
    track *= 0.9 / (np.max(np.abs(track)) + 1e-9)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    tl = {'total': total, 'scenes': scenes, 'caps': caps}
    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('// narrate.py が自動生成\nwindow.TIMELINE = ' + json.dumps(tl, ensure_ascii=False, indent=1) + ';\n')
    with open(os.path.join(HERE, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, c in enumerate(caps, 1):
            f.write(f"{i}\n{ts(c['t0'])} --> {ts(min(c['t1'] + 0.25, total))}\n{c['text'].replace(chr(10), '')}\n\n")
    print('total', total)

if __name__ == '__main__':
    main()
