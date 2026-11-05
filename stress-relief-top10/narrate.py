# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、動画全体のタイムラインを決める。
出力:
  output/narration.wav  ナレーションのみ(48kHz mono)
  output/timeline.json  シーン・字幕・効果音のタイミング(render.html / mix.py が参照)
  output/timeline.js    同内容を window.TL として読み込む用
シーンの開始は BGM の拍(120BPM)にそろえる。字幕の切り替えは AudioQuery の音素長から算出する。
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT
"""
import os, io, glob, json, wave, re
import numpy as np
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
BPM = 120
BEAT = 60 / BPM
SPEED = 1.26          # 話速(ショート向けにやや速め)

N, AMA, TSUN = 2, 0, 6   # 四国めたん: ノーマル / あまあま / ツンツン

# 各シーン: 読み上げ用テキスト(read) と 字幕表示用テキスト(disp)
# u = (read, disp, style, 後ろの間[秒])
SCENES = [
    dict(id='hook', kind='hook', u=[
        ('ねえ、ストレス、たまってない？', 'ねえ、ストレス、たまってない？', N, 0.1),
        ('今日からできる解消法、トップテン！', '今日からできる解消法 TOP10！', N, 0.15),
        ('一位は、みんなが後回しにしてる、アレ！', '1位は、みんなが後回しにしてる、アレ！', N, 0.0),
    ]),
    dict(id='r10', kind='item', rank=10, u=[('第十位、深呼吸。四秒吸って、八秒で吐くだけで、リラックスモードに！',
                                             '第10位、深呼吸。4秒吸って、8秒で吐くだけで、リラックスモードに！', N, 0)]),
    dict(id='r9', kind='item', rank=9, u=[('第九位、好きな音楽を聴く。お気に入りの一曲で、気分をリセット！',
                                           '第9位、好きな音楽を聴く。お気に入りの1曲で、気分をリセット！', N, 0)]),
    dict(id='r8', kind='item', rank=8, u=[('第八位、散歩。外を二十分歩くだけで、頭がすっきり！',
                                           '第8位、散歩。外を20分歩くだけで、頭がすっきり！', N, 0)]),
    dict(id='r7', kind='item', rank=7, u=[('第七位、湯船につかる。ぬるめのお湯に十五分で、体がほぐれるよ。',
                                           '第7位、湯船につかる。ぬるめのお湯に15分で、体がほぐれるよ。', N, 0)]),
    dict(id='r6', kind='item', rank=6, u=[('第六位、紙に書き出す。モヤモヤを言葉にすると、頭が整理されるの。',
                                           '第6位、紙に書き出す。モヤモヤを言葉にすると、頭が整理されるの。', N, 0)]),
    dict(id='r5', kind='item', rank=5, u=[('第五位、思いっきり笑う。面白い動画で、声を出して笑っちゃおう！',
                                           '第5位、思いっきり笑う。面白い動画で、声を出して笑っちゃおう！', N, 0)]),
    dict(id='r4', kind='item', rank=4, u=[('第四位、自然にふれる。木や空を眺めるだけでも、心が落ち着くよ。',
                                           '第4位、自然にふれる。木や空を眺めるだけでも、心が落ち着くよ。', N, 0)]),
    dict(id='top3', kind='top3', u=[('さあ、ここからはトップスリー！', 'さあ、ここからはTOP3！', N, 0)]),
    dict(id='r3', kind='item', rank=3, u=[('第三位、誰かに話す。聞いてもらうだけで、気持ちがぐっと軽くなるよ。',
                                           '第3位、誰かに話す。聞いてもらうだけで、気持ちがぐっと軽くなるよ。', N, 0)]),
    dict(id='r2', kind='item', rank=2, u=[
        ('第二位、スマホを置く。', '第2位、スマホを置く。', N, 0.12),
        ('って、今これ見てるあなたも、だからね？', 'って、今これ見てるあなたも、だからね？', TSUN, 0.12),
        ('寝る前の一時間だけでも、離れてみて。', '寝る前の1時間だけでも、離れてみて。', N, 0),
    ]),
    dict(id='build', kind='build', u=[('そして、第一位は。', 'そして、第1位は…', N, 0)], hold=0.6),
    dict(id='r1', kind='item', rank=1, u=[
        ('睡眠！', '睡眠！', N, 0.25),
        ('どんな解消法も、眠ってこそ効果が出るの。', 'どんな解消法も、眠ってこそ効果が出るの。', N, 0.1),
        ('今夜は、早めに寝ようね。', '今夜は、早めに寝ようね。', AMA, 0),
    ]),
    dict(id='end', kind='end', u=[
        ('どれか一つ、今日から試してみてね！', 'どれか1つ、今日から試してみてね！', N, 0.1),
        ('あなたのストレス解消法も、コメントで教えてね。', 'あなたのストレス解消法も、コメントで教えてね。', N, 0),
    ], tail=2.4),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT', '/home/user/vv/open_jtalk_dic_utf_8-1.11')
    if os.path.isdir(d): return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)

def tts(read, style):
    """音声と、句読点ごとの区切り時刻(秒, 音声先頭基準)を返す"""
    q = synth.create_audio_query(read, style)
    q.speed_scale = SPEED
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.08
    if style == TSUN: q.intonation_scale = 1.15
    wav = synth.synthesis(q, style)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    # 音素長から句ごとの終了時刻を計算(速度で割る)。実際の長さとの比で補正
    t = q.pre_phoneme_length
    bounds = []
    g = lambda o, k: (o.get(k) if isinstance(o, dict) else getattr(o, k)) or 0
    for ap in q.accent_phrases:
        for m in ap.moras:
            t += (g(m, 'consonant_length') + g(m, 'vowel_length')) / SPEED
        if ap.pause_mora is not None:
            bounds.append(t)                       # ここで句が終わる(、。)
            t += g(ap.pause_mora, 'vowel_length') / SPEED
    bounds.append(t)
    pred = t + q.post_phoneme_length
    k = (len(x) / SR) / pred
    kana = q.kana
    return x, [b * k for b in bounds], kana

def chunks(disp):
    parts = [p for p in re.split(r'(?<=[、。！？…])', disp) if p.strip()]
    return [p.rstrip('、。') for p in parts]

def q_beat(t, sub=1):
    """次の拍(sub 分割)に切り上げ"""
    g = BEAT / sub
    return np.ceil(t / g - 1e-6) * g

track = []
timeline = dict(bpm=BPM, scenes=[], captions=[], sfx=[])
cursor = 0.25
for sc in SCENES:
    start = cursor if sc['kind'] == 'hook' else q_beat(cursor)
    t = start + (0.10 if sc['kind'] != 'hook' else 0.0)
    if sc['kind'] == 'item' and sc['rank'] != 1:
        timeline['sfx'].append(dict(t=start - 0.18, type='whoosh'))
        timeline['sfx'].append(dict(t=start, type='impact'))
    if sc['kind'] == 'top3':
        timeline['sfx'].append(dict(t=start, type='impact_big'))
    if sc['kind'] == 'end':
        timeline['sfx'].append(dict(t=start, type='whoosh'))
    utts = []
    for read, disp, style, gap in sc['u']:
        x, bounds, kana = tts(read, style)
        dur = len(x) / SR
        track.append((t, x))
        cs = chunks(disp)
        if len(cs) != len(bounds):                # 区切り数が合わない時は文字数比で配分
            L = np.cumsum([len(c) for c in cs]); bounds = list(L / L[-1] * dur)
            print('  [caption fallback]', disp)
        prev = 0.0
        for c, b in zip(cs, bounds):
            timeline['captions'].append(dict(a=round(t + prev, 3), b=round(t + b, 3), text=c, scene=sc['id']))
            prev = b
        utts.append(dict(a=round(t, 3), b=round(t + dur, 3), style=style))
        print(f'{t:6.2f}s  {dur:4.2f}s  {kana[:40]}')
        t += dur + gap
    end = t + 0.25
    if sc['kind'] == 'build':
        hold = sc['hold']
        roll_a = t + 0.05
        reveal = q_beat(roll_a + hold)
        timeline['sfx'].append(dict(t=reveal, type='reveal'))
        end = reveal                               # 1位シーンは reveal 時刻ちょうどに始まる
        sc_build_reveal = reveal
    if sc['kind'] == 'end':
        end = t + sc['tail']
    timeline['scenes'].append(dict(id=sc['id'], kind=sc['kind'], rank=sc.get('rank'), a=round(start, 3), b=round(end, 3), utts=utts))
    cursor = end
    if sc['kind'] == 'build':
        cursor = sc_build_reveal - 0.10            # r1 は reveal の拍から開始(+0.1 で声)

# 各シーンの終わりを次のシーンの開始にそろえる
for a, b in zip(timeline['scenes'], timeline['scenes'][1:]):
    a['b'] = b['a']
total = round(timeline['scenes'][-1]['b'], 3)
timeline['duration'] = total
timeline['reveal'] = round(sc_build_reveal, 3)

buf = np.zeros(int((total + 0.5) * SR), dtype=np.float32)
for t, x in track:
    s = int(t * SR); buf[s:s + len(x)] += x[:len(buf) - s]
buf = buf[:int(total * SR)]
buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())

with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(timeline, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TL = ' + json.dumps(timeline, ensure_ascii=False) + ';\n')

# 字幕(SRT)
def ts(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(timeline['captions'], 1):
        f.write(f"{i}\n{ts(c['a'])} --> {ts(c['b'])}\n{c['text']}\n\n")
print(f'total {total:.2f}s  scenes={len(timeline["scenes"])} captions={len(timeline["captions"])}')
