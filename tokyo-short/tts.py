# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、各セリフの尺から動画のタイムライン(output/timeline.json)を作る。
使い方: python3 tts.py
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.18

# シーン: (id, [(読み上げ文, 字幕(【】は強調), セリフ後の間 秒, スタイルID or None)])
SCENES = [
    ('hook', [
        ('東京の秘密、九割の人が知りません。', '【9割】が知らない\n東京の秘密', 0.15, None),
        ('最後の第一位は、絶対に驚きます。', '第1位は\n【絶対に驚く】', 0.25, None),
    ]),
    ('r5', [
        ('第五位。', '第5位', 0.05, None),
        ('スカイツリーの高さは、ろっぴゃくさんじゅうよんメートル。', 'スカイツリーの高さは\n【634m】', 0.1, None),
        ('実はこれ、昔の国の名前、むさしの語呂合わせなんです。', '6・3・4で\n【む・さ・し】', 0.3, None),
    ]),
    ('r4', [
        ('第四位。', '第4位', 0.05, None),
        ('渋谷のスクランブル交差点。', '渋谷スクランブル交差点', 0.05, None),
        ('多い時は、一回の青信号で、約三千人が渡るんです。', '1回の青信号で\n約【3,000人】', 0.3, None),
    ]),
    ('r3', [
        ('第三位。', '第3位', 0.05, None),
        ('新宿駅の利用者は、一日、約三百五十万人。', '新宿駅の利用者\n1日 約【350万人】', 0.1, None),
        ('世界一利用者が多い駅として、ギネス世界記録にもなりました。', '【世界一】の駅として\nギネス世界記録に', 0.3, None),
    ]),
    ('r2', [
        ('第二位。', '第2位', 0.05, None),
        ('東京タワーの上の部分には、', '東京タワーの上部には…', 0.0, None),
        ('なんと、戦車の鉄が使われています。', 'なんと【戦車の鉄】', 0.1, None),
        ('その数、約九十台分。', '約【90台分】', 0.3, None),
    ]),
    ('r1', [
        ('そして、第一位。', 'そして… 第1位', 0.35, None),
        ('日本の一番南の島、おきのとりしま。', '日本最南端\n【沖ノ鳥島】', 0.1, None),
        ('東京から、千七百キロも離れているのに、', '東京から\n約【1,700km】', 0.0, None),
        ('住所は、なんと東京都なんです！', '住所は…\n【東京都】!!', 0.15, None),
        ('ちなみに、さいとーたんの、みなみとりしまも、東京都です。', '最東端の南鳥島も\n【東京都】', 0.3, None),
    ]),
    ('outro', [
        ('いくつ知ってた？コメントで教えてね。', 'いくつ知ってた?\n【コメント】で教えて', 0.1, None),
        ('もう一回見ると、全部覚えられるよ。', 'もう1回見て\n【全部】覚えよう', 0.2, None),
    ]),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    pyopenjtalk.g2p('東京')  # 辞書が無ければ自動ダウンロード
    return pyopenjtalk.OPEN_JTALK_DICT_DIR.decode()

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text, style):
    q = synth.create_audio_query(text, style)
    q.speed_scale = SPEED
    q.pitch_scale = 0.02
    q.intonation_scale = 1.25   # 抑揚を強めにしてショート向けのテンポ感に
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    w = synth.synthesis(q, style)
    with wave.open(io.BytesIO(w)) as r:
        sr = r.getframerate()
        x = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.005)[0]
    return x[max(0, idx[0] - 480): idx[-1] + 1440]

t = 0.25  # 冒頭は即しゃべり出す(0.25秒)
pieces, scenes = [], []
for sid, lines in SCENES:
    sc = {'id': sid, 'start': round(t, 3), 'lines': []}
    for text, sub, gap, style in lines:
        x = tts(text, style if style is not None else STYLE)
        d = len(x) / SR
        pieces.append((t, x))
        sc['lines'].append({'start': round(t, 3), 'end': round(t + d, 3), 'text': sub, 'say': text})
        t += d + gap
    sc['end'] = round(t, 3)
    scenes.append(sc)
total = round(t + 0.6, 2)
track = np.zeros(int(total * SR) + SR, dtype=np.float32)
for s, x in pieces:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(total * SR)]
track *= 0.9 / np.max(np.abs(track))
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
json.dump({'total': total, 'scenes': scenes}, open(os.path.join(OUT, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
for sc in scenes:
    print(f"{sc['id']:6s} {sc['start']:6.2f} - {sc['end']:6.2f}")
print('total', total)
