# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:青山龍星)を合成し、その長さからシーン尺・字幕・効果音のタイミングを決める。
出力:
  output/timeline.js   render.html が読むタイムライン(window.TL)
  output/narration.wav ナレーションのみ
  output/bgm.wav       BGM のみ(bgm.py で自作・権利フリー)
  output/mix.wav       ナレーション + BGM(ダッキング) + 効果音
  output/subtitles_ja.srt
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT(既定は /home/user/vv 以下)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000

NORMAL, HOT = 13, 81          # 青山龍星 ノーマル / 熱血
SPEED = {NORMAL: 1.25, HOT: 1.08}

# シーン: id, 各行 (スタイル, 読み上げ原稿, 字幕表示)  字幕の *...* は強調色
# 読み上げは誤読を避けるため数字を漢数字・カナで書く
SCENES = [
    ('hook', [
        (HOT,    'トランプ大統領の再登場で、日本はここまで変わった！', 'トランプ再登場で\n日本は*ここまで*変わった'),
        (NORMAL, '影響の大きい順に、トップファイブで解説します。', '影響の大きい順に\n*TOP5*で解説'),
        (NORMAL, '第一位は、あなたの生活にも直結します。', '第1位は\n*あなたの生活*にも直結'),
    ]),
    ('r5', [
        (HOT,    '第五位！', None),
        (NORMAL, '株と円が、大統領の一言で乱高下。', '株と円が\n大統領の*一言*で乱高下'),
        (NORMAL, '関税発表の直後、日経平均は、一日で二千六百円以上も急落しました。', '関税発表の直後\n日経平均は1日で*2,600円以上*急落'),
    ]),
    ('r4', [
        (HOT,    '第四位！', None),
        (NORMAL, '日本企業の、アメリカ移転が加速。', '日本企業の\n*アメリカ移転*が加速'),
        (NORMAL, '日本製鉄は、ユーエススチールを約二兆円で買収。', '日本製鉄は\nUSスチールを*約2兆円*で買収'),
        (NORMAL, 'ただし条件は、米政府が拒否権を持つ、黄金株でした。', '条件は 米政府が拒否権を持つ\n*黄金株*'),
    ]),
    ('r3', [
        (HOT,    '第三位！', None),
        (NORMAL, '防衛費の、増額圧力。', '防衛費の\n*増額圧力*'),
        (NORMAL, 'ナトーは、国防費をジーディーピー比、五パーセントにすることで合意。', 'NATOは国防費を\nGDP比*5%*で合意'),
        (NORMAL, '日本も、二パーセント目標の達成を、二年前倒しにしました。', '日本も*2%目標*を\n2年前倒し'),
    ]),
    ('r2', [
        (HOT,    '第二位！', None),
        (NORMAL, '約八十兆円の、対米投資。', '約*80兆円*の\n対米投資'),
        (NORMAL, '関税を下げてもらう見返りに、日本は五千五百億ドルの投資を約束。', '関税引き下げの見返りに\n*5,500億ドル*の投資を約束'),
        (NORMAL, '投資先はアメリカが主導し、回収後の利益は、九割がアメリカへ。', '投資先は米国主導\n回収後の利益は*9割*が米国へ'),
    ]),
    ('r1', [
        (HOT,    'そして、第一位！', None),
        (NORMAL, '自動車に、十五パーセントの関税。', '日本車の対米関税が\n*15%*に'),
        (NORMAL, 'かつての二点五パーセントから、六倍です。', '以前の*2.5%*から\n*6倍*に'),
        (NORMAL, '相互関税は最高裁で無効になりましたが、自動車の関税は、今も続いています。', '相互関税は最高裁で無効に\nでも*自動車関税*は継続中'),
        (NORMAL, 'トヨタだけで、年間一兆円を超える打撃です。', 'トヨタだけで\n年間*1兆円超*の打撃'),
    ]),
    ('outro', [
        (NORMAL, '同盟国だから優遇される時代は、終わりました。', '「同盟国だから優遇」の時代は\n*終わった*'),
        (NORMAL, 'あなたが一番気になったのは、何位ですか？コメントで教えてください。', '一番気になったのは何位？\n*コメント*で教えて'),
    ]),
]

# ---------------- VOICEVOX ----------------
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
VV = '/home/user/vv'
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
      f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)

def tts(text, style):
    q = synth.create_audio_query(text, style)
    q.speed_scale = SPEED[style]
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    if style == HOT:
        q.volume_scale = 1.1
    with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.005)[0]
    x = x[max(0, idx[0] - 480): idx[-1] + 1440]
    f = 240; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

# ---------------- タイムライン ----------------
clips, scenes, subs, events = [], [], [], []
t = 0.15
for sid, lines in SCENES:
    if sid == 'r1':
        t += 0.7                     # 第1位の前に「溜め」(BGMを一瞬止める)
    s0 = t
    events.append({'t': s0, 'type': 'whoosh' if sid != 'hook' else 'boom'})
    t += 0.3 if sid.startswith('r') else 0.1
    ltimes = []
    for li, (style, read, disp) in enumerate(lines):
        x = tts(read, style)
        d = len(x) / SR
        clips.append((t, x))
        ltimes.append({'t': round(t, 3), 'd': round(d, 3)})
        if disp is None:
            events.append({'t': t, 'type': 'impact', 'big': sid == 'r1'})
        else:
            subs.append({'t': t, 'end': t + d, 'text': disp})
        print(f'{sid:5s} {t:6.2f}s +{d:4.2f}s  {read[:22]}')
        t += d + (0.32 if disp is None else 0.2)
    t += 0.35
    if sid == 'outro':
        t += 1.6                     # 最後のカードを見せる時間
    scenes.append({'id': sid, 'start': round(s0, 3), 'end': round(t, 3), 'lines': ltimes})
TOTAL = round(t, 2)
# 字幕は次の字幕が出るまで表示(同じシーン内)
for i, s in enumerate(subs):
    nxt = subs[i + 1]['t'] if i + 1 < len(subs) else TOTAL
    sc = next(c for c in scenes if c['start'] <= s['t'] < c['end'])
    s['end'] = round(min(nxt, sc['end']) - 0.02, 3); s['t'] = round(s['t'], 3)
for e in events:
    e['t'] = round(e['t'], 3)
print('TOTAL', TOTAL)

with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TL = ' + json.dumps({'total': TOTAL, 'scenes': scenes, 'subs': subs, 'events': events},
                                        ensure_ascii=False, indent=1) + ';\n')

N = int(TOTAL * SR)
voice = np.zeros(N, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); voice[i:i + len(x)] += x[:N - i]
voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.9

def write(name, x):
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

# ---------------- BGM + 効果音 ----------------
import bgm
r1 = next(c for c in scenes if c['id'] == 'r1')
music = bgm.generate(TOTAL, breaks=[(r1['start'] - 0.7, r1['start'])])
sfx = bgm.sfx_track(TOTAL, events)

# ダッキング: ナレーション包絡で BGM を下げる
hop = SR // 50
rms = np.sqrt(np.mean(np.pad(voice, (0, (-len(voice)) % hop)).reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.93)
env = np.repeat(env, hop)[:N]
speech = np.clip(env / 0.08, 0, 1)
gain = 0.42 - (0.42 - 0.2) * speech
k = SR // 15
gain = np.convolve(gain, np.ones(k) / k, mode='same')

mix = voice + music * gain + sfx * 0.55
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)
write('narration.wav', voice); write('bgm.wav', music); write('sfx.wav', sfx); write('mix.wav', mix)

def ts(x):
    return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, s in enumerate(subs, 1):
        f.write(f"{i}\n{ts(s['t'])} --> {ts(s['end'])}\n{s['text'].replace('*', '')}\n\n")
print('wrote output/ (timeline.js, narration/bgm/sfx/mix.wav, subtitles_ja.srt)')
