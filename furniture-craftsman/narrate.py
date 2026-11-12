# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を文ごとに合成し、タイミング情報を書き出す。
出力: output/narration.wav / output/timing.js(render.html が読む) / output/subtitles_ja.srt
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  0.vvm を置いたディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
MAX_TOTAL = 59.0          # ショート動画として 60 秒未満に収める
LEAD, GAP, TAIL, LAST_TAIL = 0.35, 0.25, 0.4, 1.6

# シーンごとの原稿。(読み上げ用テキスト, 字幕テキスト)
SCENES = [
    ('title', [
        ('家具職人って、どんなお仕事かご存じ?', '家具職人って、どんなお仕事かご存じ?'),
        ('木と向き合うプロを、ご紹介しますわ。', '木と向き合うプロを、ご紹介しますわ。'),
    ]),
    ('work', [
        ('椅子やテーブル、たんすなどを、木材から作り上げる職人です。', '椅子やテーブル、たんすなどを木材から作り上げる職人です。'),
        ('設計から仕上げまで、一人で手がけることもあります。', '設計から仕上げまで、一人で手がけることもあります。'),
    ]),
    ('process', [
        ('まずは、きどり。木目を見きわめて、部材を切り出します。', 'まずは「木取り」。木目を見きわめて、部材を切り出します。'),
        ('続いて、かんなやノミで、形を整えます。', '続いて、かんなやノミで形を整えます。'),
        ('組み立てたら、磨いて塗装し、完成です。', '組み立てたら、磨いて塗装し、完成です。'),
    ]),
    ('joint', [
        ('見どころは、ほぞぐみなどの、木を組む技術。', '見どころは「ほぞ組み」などの、木を組む技術。'),
        ('出っぱりを穴に差し込んで、がっちり固定します。', '出っぱりを穴に差し込んで、がっちり固定します。'),
        ('ていねいに組まれた家具は、何十年も使えます。', 'ていねいに組まれた家具は、何十年も使えます。'),
    ]),
    ('move', [
        ('木は、湿気を吸ったり吐いたりして、伸び縮みします。', '木は、湿気を吸ったり吐いたりして伸び縮みします。'),
        ('その動きを読むのが、腕の見せどころです。', 'その動きを読むのが、腕の見せどころです。'),
    ]),
    ('career', [
        ('職人になるには、訓練校で学んだり、工房でしゅぎょうを積むのが一般的。', '職人になるには、訓練校で学んだり、工房で修業を積むのが一般的。'),
        ('国家資格の、家具製作技能士もあります。', '国家資格の「家具製作技能士」もあります。'),
    ]),
    ('outro', [
        ('いっしょうものの家具には、職人の技と時間が詰まっています。', '一生ものの家具には、職人の技と時間が詰まっています。'),
        ('身近な家具を見る目が、少し変わるかもしれませんわね。', '身近な家具を見る目が、少し変わるかもしれませんわね。'),
    ]),
]


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    pyopenjtalk.g2p('あ')  # 辞書が無ければ自動ダウンロードされる
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
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)

    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.05
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        if len(idx):
            x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x, q.kana


def build(engine, speed):
    """全シーンを合成して (音声クリップ配置, タイミング, 総尺) を返す"""
    t = 0.0
    clips, scenes = [], []
    for si, (sid, lines) in enumerate(SCENES):
        start = t
        t += LEAD
        ls = []
        for li, (read, cap) in enumerate(lines):
            x, kana = engine(read, speed)
            d = len(x) / SR
            clips.append((t, x))
            ls.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': cap, 'kana': kana})
            t += d + (GAP if li < len(lines) - 1 else 0)
        t += LAST_TAIL if si == len(SCENES) - 1 else TAIL
        scenes.append({'id': sid, 'start': round(start, 3), 'end': round(t, 3), 'lines': ls})
    return clips, scenes, t


def main():
    os.makedirs(OUT, exist_ok=True)
    engine = Voicevox()
    speed = 1.1
    for _ in range(5):
        clips, scenes, total = build(engine, speed)
        print(f'speed={speed:.2f} total={total:.1f}s')
        if total <= MAX_TOTAL: break
        speed *= (total / MAX_TOTAL) * 1.02
    total = round(np.ceil(total * 30) / 30, 3)  # フレーム境界に合わせる

    track = np.zeros(int(total * SR) + 1, dtype=np.float32)
    for t, x in clips:
        s = int(t * SR); e = min(s + len(x), len(track))
        track[s:e] += x[:e - s]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    for sc in scenes:
        print(f"[{sc['id']}] {sc['start']:.2f}–{sc['end']:.2f}")
        for l in sc['lines']:
            print(f"   {l['start']:6.2f}–{l['end']:6.2f}  {l['kana']}")
    timing = {'total': total, 'speed': round(speed, 3),
              'scenes': [{**sc, 'lines': [{k: v for k, v in l.items() if k != 'kana'} for l in sc['lines']]} for sc in scenes]}
    with open(os.path.join(OUT, 'timing.js'), 'w', encoding='utf-8') as f:
        f.write('window.TIMING = ' + json.dumps(timing, ensure_ascii=False, indent=1) + ';\n')

    def ts(t):
        ms = int(round(t * 1000))
        return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        i = 1
        for sc in scenes:
            for l in sc['lines']:
                f.write(f"{i}\n{ts(l['start'])} --> {ts(l['end'] + 0.2)}\n{l['text']}\n\n"); i += 1
    print('total', total)


if __name__ == '__main__':
    main()
