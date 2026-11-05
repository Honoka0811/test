# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その長さから動画のタイムラインを決める。
出力:
  output/narration.wav  ナレーションのみ(48kHz モノラル)
  timeline.js           render.html / mix.py が読むシーン・発話のタイミング
  output/subtitles_ja.srt
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  0.vvm(四国めたん)を置いたディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, glob, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.3

# 各シーン: id, 発話リスト [(読み上げ原稿, 字幕表示, 発話前の間(秒))], シーン末尾の余白
# 読み上げ原稿は誤読を避けるため一部かな書き。
SCENES = [
    ('intro', [('戦前の日本の、人口ランキング!今とは全然違うのよ。', '戦前の日本の人口ランキング!今とは全然違うのよ。', 0.5)], 0.45),
    ('r10', [('十位、広島県、百八十七万人。軍港くれのある、海軍の町よ。', '10位、広島県、187万人。軍港・呉のある海軍の町よ。', 0.35)], 0.2),
    ('r9', [('九位、静岡県、二百二万人。お茶とみかんで栄えたわ。', '9位、静岡県、202万人。お茶とみかんで栄えたわ。', 0.35)], 0.2),
    ('r8', [('八位、新潟県、二百六万人。明治には、人口日本一だったの!', '8位、新潟県、206万人。明治には人口日本一だったの!', 0.35)], 0.2),
    ('r7', [('七位、神奈川県、二百十九万人。今は全国二位まで大躍進!', '7位、神奈川県、219万人。今は全国2位まで大躍進!', 0.35)], 0.2),
    ('r6', [('六位、福岡県、三百九万人。製鉄所と炭鉱の県よ。', '6位、福岡県、309万人。製鉄所と炭鉱の県よ。', 0.35)], 0.2),
    ('r5', [('五位、愛知県、三百十七万人。飛行機づくりの拠点だったわ。', '5位、愛知県、317万人。飛行機づくりの拠点だったわ。', 0.35)], 0.2),
    ('r4', [('四位、兵庫県、三百二十二万人。港町神戸は、日本の玄関口よ。', '4位、兵庫県、322万人。港町・神戸は日本の玄関口よ。', 0.35)], 0.2),
    ('r3', [('ここからトップスリー!三位は、', 'ここからTOP3!3位は…', 0.4),
            ('北海道!三百二十七万人。開拓で人口が急増したの。', '北海道!327万人。開拓で人口が急増したの。', 0.95)], 0.2),
    ('r2', [('二位は、', '2位は…', 0.35),
            ('大阪府!四百七十九万人。だいおおさかと呼ばれた大都市よ。', '大阪府!479万人。「大大阪」と呼ばれた大都市よ。', 0.8)], 0.2),
    ('r1', [('そして、一位は、', 'そして1位は…', 0.4),
            ('東京府!七百三十五万人。まだ東京都じゃなかったのよ。', '東京府!735万人。まだ「東京都」じゃなかったのよ。', 1.3)], 0.4),
    ('outro', [('あなたの県は何位だった?コメントで教えてね!', 'あなたの県は何位だった?コメントで教えてね!', 0.35)], 2.6),
]


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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next(c.name + '/' + st.name for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)

    def __call__(self, text, speed=SPEED, pitch=0.0, intonation=1.15):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pitch_scale = pitch
        q.intonation_scale = intonation
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(self.synth.synthesis(q, self.style))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 600): idx[-1] + 2400]
        f = min(480, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x


def main():
    tts = Voicevox()
    clips, scenes, t = [], [], 0.0
    for sid, utts, tail in SCENES:
        start = t
        us = []
        for i, (text, disp, gap) in enumerate(utts):
            # 順位発表の「〜は、」はためを作るため少しゆっくり・抑揚強め
            suspense = sid in ('r3', 'r2', 'r1') and i == 0
            x = tts(text, speed=SPEED * (0.95 if suspense else 1.0), intonation=1.3 if suspense else 1.15)
            t += gap
            us.append({'start': round(t, 3), 'end': round(t + len(x) / SR, 3), 'text': disp})
            clips.append((t, x))
            t += len(x) / SR
        t += tail
        scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3), 'utts': us})
        print(f'{sid:6s} {start:6.2f} → {t:6.2f}  ({t - start:4.2f}s)')
    total = round(t, 3)

    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, x in clips:
        s = int(st * SR); track[s:s + len(x)] += x
    track = track[:int(total * SR)]
    track = track / (np.max(np.abs(track)) or 1) * 0.9
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('// 生成: narrate.py(ナレーションの長さから決まるタイムライン)\n')
        f.write('window.TIMELINE=' + json.dumps({'total': total, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')

    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    n = 0
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for sc in scenes:
            for u in sc['utts']:
                n += 1
                f.write(f"{n}\n{ts(u['start'])} --> {ts(min(u['end'] + 0.25, total))}\n{u['text']}\n\n")
    print('total', total, 's')


if __name__ == '__main__':
    main()
