# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を一文ずつ合成し、シーン尺と字幕タイミングを決める。
出力: output/narration.wav, output/subtitles_ja.srt, timings.js(render.html が読む)
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.18       # 話速
GAP = 0.30         # 文と文の間
LEAD = 0.6         # シーン頭の間
TAIL = 0.7         # シーン末尾の間
END_CARD = 3.5     # クレジット

# シーンごとに (読み上げ文, 字幕表記) のリスト。render.html の SCENE_DRAW と同じ順番
SCENES = [
    [('昭和のにほんを震撼させた、劇場型犯罪。', '昭和の日本を震撼させた、劇場型犯罪。'),
     ('グリコ・森永事件。', 'グリコ・森永事件。'),
     ('その犯人は、いまだに捕まっていません。', 'その犯人は、いまだに捕まっていません。')],
    [('千九百八十四年三月、江崎グリコの社長が、自宅から誘拐されます。', '1984年3月、江崎グリコの社長が、自宅から誘拐されます。'),
     ('要求は、現金十億円と、金塊百キロ。', '要求は、現金10億円と、金塊100キロ。'),
     ('社長は三日後、自力で脱出しました。', '社長は3日後、自力で脱出しました。')],
    [('やがて犯人は、マスコミに挑戦状を送りつけます。', 'やがて犯人は、マスコミに挑戦状を送りつけます。'),
     ('名乗った名は、かい人にじゅういちめんそう。', '名乗った名は、「かい人21面相」。'),
     ('警察をあざ笑う、関西弁の手紙でした。', '警察をあざ笑う、関西弁の手紙でした。')],
    [('標的は、丸大食品、森永製菓、ハウス食品へと広がっていきます。', '標的は、丸大食品、森永製菓、ハウス食品へと広がっていきます。'),
     ('そして店頭には、青酸ソーダ入りの菓子が置かれました。', 'そして店頭には、青酸ソーダ入りの菓子が置かれました。'),
     ('どくいり、きけん。たべたら、しぬで。', '「どくいり きけん たべたら 死ぬで」')],
    [('警察は、何度も犯人に迫りました。', '警察は、何度も犯人に迫りました。'),
     ('現金の受け渡し現場で目撃された、キツネ目の男。', '現金の受け渡し現場で目撃された、「キツネ目の男」。'),
     ('しかし、あと一歩のところで、取り逃がします。', 'しかし、あと一歩のところで、取り逃がします。')],
    [('千九百八十五年八月、滋賀県警の本部長が、焼身自殺。', '1985年8月、滋賀県警の本部長が、焼身自殺。'),
     ('その五日後、犯人は一方的に、終結を宣言しました。', 'その5日後、犯人は一方的に、終結を宣言しました。'),
     ('くいもんの会社、いびるの、もお、やめや。', '「くいもんの 会社 いびるの もお やめや」')],
    [('二千年二月、すべての事件で、時効が成立。', '2000年2月、すべての事件で、時効が成立。'),
     ('かい人にじゅういちめんそうの正体は、今も、闇の中です。', '「かい人21面相」の正体は、今も、闇の中です。')],
]

class Engine:
    def __init__(self):
        import pyopenjtalk
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(pyopenjtalk.OPEN_JTALK_DICT_DIR.decode()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        print('engine: VOICEVOX', next(c.name + '/' + s.name for c in self.synth.metas() for s in c.styles if s.id == self.style))

    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = SPEED
        q.pitch_scale = -0.02      # わずかに低く、落ち着いたトーンに
        q.intonation_scale = 0.9
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.05
        with wave.open(io.BytesIO(self.synth.synthesis(q, self.style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        x = x[max(0, idx[0] - 600): idx[-1] + 2400]
        f = 400
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x

def main():
    eng = Engine()
    clips, scenes, cues = [], [], []
    t = 0.0
    for si, lines in enumerate(SCENES):
        start = t
        t += LEAD
        for read, sub in lines:
            x = eng(read)
            clips.append((t, x))
            cues.append({'scene': si, 'start': round(t, 3), 'end': round(t + len(x) / SR, 3), 'text': sub})
            t += len(x) / SR + GAP
        t += TAIL - GAP
        scenes.append({'start': round(start, 3), 'dur': round(t - start, 3)})
        print(f'scene {si}: {start:5.2f}s +{t - start:5.2f}s')
    scenes.append({'start': round(t, 3), 'dur': END_CARD})
    total = round(t + END_CARD, 3)

    track = np.zeros(int(total * SR) + 1, dtype=np.float32)
    for s, x in clips:
        i = int(s * SR); track[i:i + len(x)] += x
    track = track / np.max(np.abs(track)) * 0.85
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    with open(os.path.join(HERE, 'timings.js'), 'w', encoding='utf-8') as f:
        f.write('// narrate.py が自動生成\nwindow.TIMINGS = ' +
                json.dumps({'total': total, 'scenes': scenes, 'cues': cues}, ensure_ascii=False, indent=1) + ';\n')

    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{ts(c['start'])} --> {ts(c['end'] + 0.2)}\n{c['text']}\n\n")
    print('total', total, 's')

if __name__ == '__main__':
    main()
