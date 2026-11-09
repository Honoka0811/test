# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を文単位で合成し、実測した長さからシーン尺・字幕タイミングを決める。
出力:
  output/narration.wav  ナレーションのみ
  timeline.js           render.html が読み込むシーン尺と字幕キュー
  output/subtitles_ja.srt
使い方: python3 narrate.py
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')

SR = 48000
SPEED = 1.12     # 話速
LEAD = 0.45      # シーン開始から最初の発話まで
GAP = 0.28       # 文と文の間
TAIL = 0.55      # 最後の発話からシーン終了まで
END_HOLD = 2.2   # 最終シーンの余韻

# シーンID と (読み上げ用テキスト, 字幕テキスト) のリスト。render.html の SCENE_FUNCS と対応
SCRIPT = [
    ('title', [
        ('あなたの周りにも、いるかもしれません。', 'あなたの周りにも、いるかもしれません。'),
        ('友達のふりをした敵、フレネミー。', '友達のふりをした敵、「フレネミー」。'),
    ]),
    ('define', [
        ('フレネミーとは、フレンドとエネミーを合わせた言葉。', 'フレネミーとは、Friend(友達)とEnemy(敵)を合わせた言葉。'),
        ('表では仲良くしながら、裏であなたの足を引っ張る人のことです。', '表では仲良くしながら、裏であなたの足を引っ張る人のことです。'),
    ]),
    ('praise', [
        ('特徴その一。褒めると見せかけて、さりげなく落とす。', '特徴① 褒めると見せかけて、さりげなく落とす。'),
        ('かわいいね、安かったでしょ?なんて言葉に、心当たりはありませんか。', '「かわいいね、安かったでしょ?」…心当たりはありませんか?'),
    ]),
    ('success', [
        ('その二。あなたの成功を、素直に喜ばない。', '特徴② あなたの成功を、素直に喜ばない。'),
        ('うれしい報告をしても、運が良かっただけだよ、と水を差します。', 'うれしい報告をしても「運が良かっただけだよ」と水を差します。'),
    ]),
    ('secret', [
        ('その三。打ち明けた秘密が、いつの間にか広まっている。', '特徴③ 打ち明けた秘密が、いつの間にか広まっている。'),
        ('うわさの出どころは、たいていその人です。', 'うわさの出どころは、たいていその人です。'),
    ]),
    ('divide', [
        ('その四。あの子があなたの悪口を言ってたよ、と告げ口して、', '特徴④「あの子が悪口言ってたよ」と告げ口して、'),
        ('ほかの人との仲を、引き裂こうとします。', 'ほかの人との仲を引き裂こうとします。'),
    ]),
    ('check', [
        ('会ったあと、どっと疲れる。なぜか自信がなくなる。', '会ったあと、どっと疲れる。なぜか自信がなくなる。'),
        ('そう感じたら、それは要注意のサインです。', 'そう感じたら、それは要注意のサインです。'),
    ]),
    ('cope', [
        ('対処法は三つ。少しずつ距離を置く。', '対処法は3つ。少しずつ距離を置く。'),
        ('大切な情報は話さない。', '大切な情報は話さない。'),
        ('そして、挑発には反応しないこと。', 'そして、挑発には反応しないこと。'),
    ]),
    ('outro', [
        ('一緒にいて、心が軽くなる人。', '一緒にいて、心が軽くなる人。'),
        ('そんな友達を、大切にしてくださいね。', 'そんな友達を、大切にしてくださいね。'),
    ]),
]


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    return os.path.join(VV, 'open_jtalk_dic_utf_8-1.11')


class Voicevox:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get(
            'VOICEVOX_ORT', os.path.join(VV, 'ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so')))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', os.path.join(VV, 'vvms')), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next(c.name + '/' + st.name for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)

    def __call__(self, text):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = SPEED
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


def main():
    tts = Voicevox()
    clips, scenes, cues = [], [], []
    t = 0.0
    for si, (sid, lines) in enumerate(SCRIPT):
        start = t
        t += LEAD
        for li, (read, disp) in enumerate(lines):
            x = tts(read)
            clips.append((t, x))
            d = len(x) / SR
            cues.append({'s': round(t, 3), 'e': round(t + d, 3), 'text': disp, 'scene': sid})
            t += d + (GAP if li < len(lines) - 1 else 0)
        t += TAIL + (END_HOLD if si == len(SCRIPT) - 1 else 0)
        scenes.append({'id': sid, 's': round(start, 3), 'd': round(t - start, 3)})
        print(f'{sid:8s} {start:5.2f}s +{t - start:5.2f}s')
    total = round(t, 3)

    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for s, x in clips:
        i = int(s * SR); track[i:i + len(x)] += x
    track = track[:int(total * SR)]
    track = track / (np.max(np.abs(track)) or 1) * 0.85
    with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())

    with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('// narrate.py が自動生成(手で編集しない)\n')
        f.write('window.TIMELINE = ' + json.dumps({'total': total, 'scenes': scenes, 'cues': cues},
                                                  ensure_ascii=False, indent=1) + ';\n')

    def ts(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{ts(c['s'])} --> {ts(min(c['e'] + 0.25, total))}\n{c['text']}\n\n")
    print(f'total {total:.2f}s  -> output/narration.wav, timeline.js, output/subtitles_ja.srt')


if __name__ == '__main__':
    main()
