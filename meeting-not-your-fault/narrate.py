# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その長さからタイムラインを決める。
出力:
  output/narration.wav  ナレーションのみ(48kHz mono)
  timeline.js           render.html が読むシーン/セリフのタイミング
  output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.12

# シーンID, 読み上げ原稿, 字幕(表示用), スタイル(None=既定)
# シーン: hook / blame / question / coop / signs1-3 / signs_sum / tip / relief / end
LINES = [
    ('hook',     '会議で、何が言いたいの？とか、で、何がしたいの？って、言われたこと、ありませんか？',
                 '会議で「何が言いたいの？」「で、何がしたいの？」って言われたこと、ありませんか？', None),
    ('blame',    'そう言われると、説明が下手な自分が悪いんだって、落ち込んでしまいますよね。',
                 'そう言われると「説明が下手な自分が悪いんだ」って落ち込んでしまいますよね。', None),
    ('question', 'でも、ちょっと待って。それ、本当に、あなただけのせいでしょうか？',
                 'でも、ちょっと待って。それ、本当にあなただけのせいでしょうか？', None),
    ('coop',     '会話は、話す人と聞く人の、共同作業。伝わらない原因が、聞く側にあることも、実は少なくありません。',
                 '会話は、話す人と聞く人の共同作業。伝わらない原因が、聞く側にあることも実は少なくありません。', None),
    ('signs1',   'たとえば、話を最後まで聞かずに、途中で遮ってくる。',
                 'たとえば、話を最後まで聞かずに途中で遮ってくる。', None),
    ('signs2',   'どこが分からないのかは言わずに、責める言葉だけを投げてくる。',
                 'どこが分からないのかは言わずに、責める言葉だけを投げてくる。', None),
    ('signs3',   'そもそも、会議の目的や前提を、ちゃんと共有していない。',
                 'そもそも、会議の目的や前提をちゃんと共有していない。', None),
    ('signs_sum', 'こんなときは、相手の聞き方にも、問題があるかもしれません。',
                 'こんなときは、相手の聞き方にも問題があるかもしれません。', None),
    ('tip',      'そんなときは、どの部分が分かりにくかったですか？と、具体的に聞き返してみましょう。責める言葉を、質問に変えてもらうのがコツです。',
                 'そんなときは「どの部分が分かりにくかったですか？」と具体的に聞き返してみましょう。責める言葉を、質問に変えてもらうのがコツです。', None),
    ('relief',   '伝え方を工夫するのは、もちろん大切。でも、全部を一人で、抱え込まなくて大丈夫。',
                 '伝え方を工夫するのは、もちろん大切。でも、全部を一人で抱え込まなくて大丈夫。', None),
    ('end',      '伝わらないのは、あなただけのせいじゃない。',
                 '伝わらないのは、あなただけのせいじゃない。', 0),  # 0 = 四国めたん あまあま
]
INTRO = 0.5    # 動画冒頭の間
GAP = 0.35     # 同じシーン内のセリフ間
SCENE_GAP = 0.7  # シーンが切り替わる前の余韻
SIGN_GAP = 0.5
TAIL = 3.0     # 最後のセリフ後の余韻(エンドカード)

class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.s = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', '/home/user/vv/open_jtalk_dic_utf_8-1.11')))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.s.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))

    def __call__(self, text, style=None):
        st = self.style if style is None else style
        q = self.s.create_audio_query(text, st)
        q.speed_scale = SPEED
        q.intonation_scale = 1.15
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        with wave.open(io.BytesIO(self.s.synthesis(q, st))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        idx = np.where(np.abs(x) > 0.004)[0]
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
        f = min(600, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        return x

def main():
    tts = Voicevox()
    clips, lines = [], []
    t = INTRO
    for i, (scene, text, sub, style) in enumerate(LINES):
        x = tts(text, style)
        d = len(x) / SR
        lines.append({'scene': scene, 'start': round(t, 3), 'end': round(t + d, 3), 'text': sub})
        clips.append((t, x))
        print(f'{t:6.2f}s  {d:5.2f}s  {scene:9s} {sub[:20]}…')
        nxt = LINES[i + 1][0] if i + 1 < len(LINES) else None
        if nxt is None: gap = TAIL
        elif nxt == scene: gap = GAP
        elif scene.startswith('signs') and nxt.startswith('signs'): gap = SIGN_GAP
        else: gap = SCENE_GAP
        t += d + gap
    total = round(t, 2)

    # シーン区間: シーン内最初のセリフ開始の少し前 → 次シーン開始
    scenes = []
    for ln in lines:
        name = 'signs' if ln['scene'].startswith('signs') else ln['scene']
        if not scenes or scenes[-1]['name'] != name:
            scenes.append({'name': name, 'start': 0 if not scenes else round(ln['start'] - 0.25, 3)})
    for a, b in zip(scenes, scenes[1:] + [{'start': total}]):
        a['end'] = b['start']

    track = np.zeros(int(total * SR), dtype=np.float32)
    for s, x in clips:
        i = int(s * SR); track[i:i + len(x)] += x[:len(track) - i]
    track = track / np.max(np.abs(track)) * 0.85
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    tl = {'duration': total, 'scenes': scenes, 'lines': lines}
    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('// narrate.py が生成(手で編集しない)\nwindow.TL = ' + json.dumps(tl, ensure_ascii=False, indent=1) + ';\n')

    def ts(v):
        return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for k, ln in enumerate(lines, 1):
            f.write(f"{k}\n{ts(ln['start'])} --> {ts(min(ln['end'] + 0.3, total))}\n{ln['text']}\n\n")
    print('total', total, 's')

if __name__ == '__main__':
    main()
