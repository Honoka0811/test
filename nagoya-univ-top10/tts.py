# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その長さからシーンのタイミングを決めて
output/narration.wav / output/subtitles_ja.srt / timeline.js を書き出す。
環境変数: VOICEVOX_ORT, VOICEVOX_VVMS, VOICEVOX_DICT, VOICEVOX_STYLE(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, glob, wave
import numpy as np
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = 1.3
LEAD = 0.35   # シーン開始から発話開始まで
TAIL = 0.45   # 発話終了から次のシーンまで

# (種別, 番号, 見出し, 補足, 字幕テキスト, 読み上げテキスト)
SCENES = [
    ('intro', 0, '名古屋大学の\nここがすごい！', '10選',
     '名古屋大学のここがすごい！10選、いきますわよ！',
     'なごやだいがくの、ここがすごい！じゅっせん、いきますわよ！'),
    ('item', 1, '21世紀のノーベル賞\n受賞者が6人', '野依良治・小林誠・益川敏英\n下村脩・赤﨑勇・天野浩',
     '21世紀に入ってからのノーベル賞受賞者は、なんと6人。日本の大学でもトップクラスですわ。',
     'にじゅういっせいきに入ってからの、ノーベル賞受賞者は、なんと六人。日本の大学でもトップクラスですわ。'),
    ('item', 2, '青色LEDを\n生んだ大学', '2014年 ノーベル物理学賞',
     'ノーベル物理学賞の青色LEDは、赤﨑勇さんと天野浩さんが名大で切り開いた研究ですの。',
     'ノーベル物理学賞の青色エルイーディーは、あかさきいさむさんと、あまのひろしさんが、めいだいで切り開いた研究ですの。'),
    ('item', 3, '最後に誕生した\n帝国大学', '1939年 名古屋帝国大学',
     '1939年、国内で7番目の帝国大学として誕生。いわゆる旧帝大のひとつですわ。',
     'せんきゅうひゃくさんじゅうきゅうねん、国内で七番目の帝国大学として誕生。いわゆる、きゅうていだいの、ひとつですわ。'),
    ('item', 4, 'キャンパスに\n地下鉄の駅', '地下鉄名城線「名古屋大学」駅',
     'キャンパスの中に地下鉄の駅があって、その名も「名古屋大学駅」。通学がとっても楽ですの。',
     'キャンパスの中に、地下鉄の駅があって、その名も、なごやだいがくえき。通学がとっても楽ですの。'),
    ('item', 5, 'シンボルは\n豊田講堂', '1960年竣工・設計 槇文彦',
     'シンボルの豊田講堂は、トヨタ自動車の寄付で建てられた、名建築なのですわ。',
     'シンボルの、とよたこうどうは、トヨタ自動車の寄付で建てられた、名建築なのですわ。'),
    ('item', 6, 'ノーベル賞\n展示館がある', '受賞者ゆかりの資料を展示',
     'キャンパスにはノーベル賞展示館まであって、受賞者ゆかりの資料を見学できますの。',
     'キャンパスには、ノーベル賞展示館まであって、受賞者ゆかりの資料を、見学できますの。'),
    ('item', 7, '日本初の\n「1法人複数大学」', '2020年 東海国立大学機構（岐阜大学と）',
     '2020年、岐阜大学と東海国立大学機構を設立。ひとつの法人で複数の国立大学を運営する、日本初の形ですわ。',
     'にせんにじゅうねん、ぎふだいがくと、とうかいこくりつだいがくきこうを設立。ひとつの法人で、複数の国立大学を運営する、日本初の形ですわ。'),
    ('item', 8, '指定国立大学法人', '世界最高水準をめざす大学に選定',
     '世界と競える大学として、指定国立大学法人にも選ばれていますの。',
     '世界と競える大学として、していこくりつだいがくほうじんにも、選ばれていますの。'),
    ('item', 9, '防災研究の拠点\n「減災館」', '建物そのものが免震構造',
     '防災研究の拠点「減災館」は、建物そのものが免震構造。研究も備えも本格派ですわ。',
     '防災研究の拠点、げんさいかんは、建物そのものが、免震構造。研究も備えも、本格派ですわ。'),
    ('item', 10, '自由闊達な学風', '名古屋大学学術憲章より',
     'そして何より、自由闊達な学風。のびのび挑戦できるのが、名大いちばんの魅力ですわ。',
     'そして何より、じゆうかったつな学風。のびのび挑戦できるのが、めいだい、いちばんの魅力ですわ。'),
    ('outro', 0, 'どれが一番\nすごかった？', 'コメントで教えてね',
     'あなたはどれが一番すごいと思いました？コメントで教えてくださいまし！',
     'あなたは、どれが一番すごいと思いました？コメントで、教えてくださいまし！'),
]


def dict_dir():
    if os.environ.get('VOICEVOX_DICT'):
        return os.environ['VOICEVOX_DICT']
    return '/home/user/vv/open_jtalk_dic_utf_8-1.11'


ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))


def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.pitch_scale = 0.02
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    f = min(600, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x


clips, timeline, t = [], [], 0.0
for kind, num, title, sub, subtitle, reading in SCENES:
    x = tts(reading)
    dur = LEAD + len(x) / SR + TAIL
    if kind == 'outro':
        dur += 1.2  # 余韻
    clips.append((t + LEAD, x))
    timeline.append(dict(kind=kind, num=num, title=title, sub=sub, subtitle=subtitle,
                         start=round(t, 3), dur=round(dur, 3),
                         vstart=round(t + LEAD, 3), vend=round(t + LEAD + len(x) / SR, 3)))
    print(f'{t:6.2f}s  {dur:5.2f}s  {subtitle[:20]}')
    t += dur

TOTAL = round(t, 3)
track = np.zeros(int(np.ceil(TOTAL * SR)), dtype=np.float32)
for s, x in clips:
    i = int(s * SR)
    track[i:i + len(x)] += x[:len(track) - i]
track *= 0.85 / np.max(np.abs(track))
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// tts.py が自動生成\nwindow.TIMELINE = ' + json.dumps(timeline, ensure_ascii=False, indent=1) +
            ';\nwindow.DURATION = ' + str(TOTAL) + ';\n')


def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'


with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, s in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(s['vstart'])} --> {ts(min(s['vend'] + 0.3, TOTAL))}\n{s['subtitle']}\n\n")
print('total', TOTAL, 's')
