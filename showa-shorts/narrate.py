# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その長さからシーンのタイムラインを決める。
出力: output/narration.wav, output/timeline.json, output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT
"""
import os, io, json, wave, glob
import numpy as np
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
NORMAL, AMA, TSUN = 2, 0, 6   # 四国めたん ノーマル / あまあま / ツンツン

# 各シーン: kind, 表示用データ, ナレーション [(読み上げ文, 字幕文, スタイル, 速度)]
SCENES = [
    dict(kind='hook', lines=[
        ('昭和では当たり前。でも令和なら、大炎上！？', '昭和では当たり前。でも令和なら大炎上!?', TSUN, 1.15),
        ('今じゃ考えられない、昭和の常識ベストファイブ！', '今じゃ考えられない 昭和の常識ベスト5!', NORMAL, 1.2),
    ]),
    dict(kind='rank', rank=5, emoji='🚬', sub='✈️', head=['飛行機の中で', 'タバコが吸えた'],
         stat=['男性の喫煙率', '83.7%'], note='1966年 / 国内線の全面禁煙は1999年',
         lines=[
        ('第五位。飛行機の中でも、タバコが吸えた。', '第5位。飛行機の中でも、タバコが吸えた。', NORMAL, 1.2),
        ('当時、男性の喫煙率は、なんと八割以上！', '当時、男性の喫煙率はなんと8割以上!', NORMAL, 1.2),
    ]),
    dict(kind='rank', rank=4, emoji='🛒', sub='🧾', head=['買い物に', '消費税がなかった'],
         stat=['消費税', '0%'], note='消費税の導入は1989年4月(平成元年)',
         lines=[
        ('第四位。買い物に、消費税がなかった。', '第4位。買い物に、消費税がなかった。', NORMAL, 1.2),
        ('消費税が始まったのは、平成になってからなんです。', '消費税が始まったのは、平成になってからなんです。', NORMAL, 1.2),
    ]),
    dict(kind='rank', rank=3, emoji='🎫', sub='✂️', head=['駅員さんが', '切符にハサミ'],
         stat=['改札の音', 'カチカチ♪'], note='自動改札が広まる前は、駅員さんの手作業でした',
         lines=[
        ('第三位。駅の改札で、駅員さんが切符にハサミを入れていた。', '第3位。駅の改札で、駅員さんが切符にハサミを入れていた。', NORMAL, 1.25),
        ('カチカチという、あの音。覚えていますか？', 'カチカチというあの音、覚えていますか?', AMA, 1.15),
    ]),
    dict(kind='rank', rank=2, emoji='☎️', sub='💓', head=['電話は', '家に1台だけ'],
         stat=['好きな人に電話', 'お父さんが出る'], note='ダイヤル式の黒電話が主役でした',
         lines=[
        ('第二位。電話は、家に一台だけ。', '第2位。電話は、家に1台だけ。', NORMAL, 1.2),
        ('好きな人の家にかけたら、お父さんが出ちゃうことも……', '好きな人の家にかけたら、お父さんが出ちゃうことも…', AMA, 1.15),
    ]),
    dict(kind='tease', lines=[
        ('そして第一位は、今の子どもには、信じられないかも。', 'そして第1位は、今の子どもには信じられないかも…', NORMAL, 1.15),
    ]),
    dict(kind='rank', rank=1, emoji='🏫', sub='🎒', head=['土曜日も', '学校があった'],
         stat=['土曜日は', '半ドン'], note='学校の完全週5日制は2002年から',
         lines=[
        ('第一位。土曜日も、学校があった！', '第1位。土曜日も、学校があった!', TSUN, 1.15),
        ('お昼で帰れる、いわゆる、半ドンです。', 'お昼で帰れる、いわゆる「半ドン」です。', NORMAL, 1.2),
    ]),
    dict(kind='outro', lines=[
        ('あなたは、いくつ知ってましたか？', 'あなたは、いくつ知ってましたか?', AMA, 1.15),
        ('コメントで教えてね！', 'コメントで教えてね!', AMA, 1.15),
    ]),
]

# シーン内の間(秒)
LEAD = {'hook': 0.25, 'rank': 0.75, 'tease': 0.2, 'outro': 0.3}   # rank は番号ドーン!の後に話し始める
GAP = 0.3
TAIL = {'hook': 0.35, 'rank': 0.9, 'tease': 0.45, 'outro': 1.6}

def dict_dir():
    if os.environ.get('VOICEVOX_DICT'): return os.environ['VOICEVOX_DICT']
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'dictionary')

ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)

def tts(text, style, speed):
    q = synth.create_audio_query(text, style)
    q.speed_scale = speed
    q.intonation_scale = 1.25          # 抑揚を少し強めてショート向けのテンポ感に
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = min(400, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips, timeline, t = [], [], 0.0
for sc in SCENES:
    start = t
    t += LEAD[sc['kind']]
    lines = []
    for i, (say, cap, style, speed) in enumerate(sc['lines']):
        if i: t += GAP
        x = tts(say, style, speed)
        clips.append((t, x))
        lines.append(dict(start=round(t, 3), end=round(t + len(x) / SR, 3), text=cap))
        t += len(x) / SR
    t += TAIL[sc['kind']]
    d = {k: v for k, v in sc.items() if k != 'lines'}
    d.update(start=round(start, 3), end=round(t, 3), lines=lines)
    timeline.append(d)
    print(f"{sc['kind']:6s} {start:6.2f} → {t:6.2f}  ({t - start:4.2f}s)")

TOTAL = round(t, 2)
track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) + 1e-9) * 0.9
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
json.dump(dict(total=TOTAL, scenes=timeline), open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 0
    for sc in timeline:
        for ln in sc['lines']:
            n += 1
            f.write(f"{n}\n{ts(ln['start'])} --> {ts(min(ln['end'] + 0.2, TOTAL))}\n{ln['text']}\n\n")
print('total', TOTAL, 's')
