# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その実尺からシーンの長さを決めて timings.js に書き出す。
さらに BGM(bgm.py)をナレーション中だけ下げてミックスし output/mix.wav を作る。
使い方: python3 narrate.py   → 続けて node capture.js && ./mux.sh
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
VV = '/home/user/vv'
SR = 48000
SPEED = 1.18
LEAD = 0.35   # シーン開始 → 発話開始
TAIL = 0.55   # 発話終了 → 次のシーン

# (シーンID, 読み上げ原稿, 字幕表記)
SCRIPT = [
    ('title', 'ギロチン。それはもともと、人道的な処刑のために生まれた機械でした。',
              'ギロチン。それはもともと「人道的な処刑」のために生まれた機械でした。'),
    ('before', 'かつてのフランスでは、貴族は剣で斬首、庶民は絞首刑や車ざきと、身分によって処刑の方法が違いました。',
               'かつてのフランスでは、貴族は剣で斬首、庶民は絞首刑や車裂きと、身分によって処刑の方法が違いました。'),
    ('guillotin', '千七百八十九年、医師ギヨタンは、全ての死刑囚を、同じ方法で、苦痛なく処刑すべきだと議会に提案します。',
                  '1789年、医師ギヨタンは「すべての死刑囚を、同じ方法で、苦痛なく処刑すべきだ」と議会に提案します。'),
    ('machine', '設計したのは外科医アントワーヌ・ルイ。斜めの刃が確実さを生み、千七百九十二年、最初の執行が行われました。',
                '設計したのは外科医アントワーヌ・ルイ。斜めの刃が確実さを生み、1792年、最初の執行が行われました。'),
    ('terror', 'そして恐怖政治の時代。フランス全土で、およそ一万七千人が死刑判決を受けました。',
               'そして恐怖政治の時代。フランス全土で、およそ1万7千人が死刑判決を受けました。'),
    ('names', 'ルイ十六世、マリー・アントワネット、そして恐怖政治を率いたロベスピエール自身も、この刃で命を落とします。',
              'ルイ16世、マリー・アントワネット、そして恐怖政治を率いたロベスピエール自身も、この刃で命を落とします。'),
    ('crowd', '処刑は公開され、広場には大勢の見物人が集まりました。ミニチュアのギロチンが、おもちゃとして売られるほどでした。',
              '処刑は公開され、広場には大勢の見物人が集まりました。ミニチュアのギロチンが、おもちゃとして売られるほどでした。'),
    ('end', '最後の公開処刑は千九百三十九年。最後の執行は千九百七十七年。そして千九百八十一年、フランスは死刑を廃止しました。',
            '最後の公開処刑は1939年。最後の執行は1977年。そして1981年、フランスは死刑を廃止しました。'),
    ('trivia', 'ちなみに、ギヨタン本人はギロチンで処刑されていません。名前だけが、残ってしまったのです。',
               'ちなみに、ギヨタン本人はギロチンで処刑されていません。名前だけが残ってしまったのです。'),
]
OUTRO = 2.5  # 最後のクレジット表示

def load_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
        f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
    synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    style = int(os.environ.get('VOICEVOX_STYLE', '2'))
    name = next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == style)
    print('engine: VOICEVOX', name)
    return synth, style

synth, STYLE = load_engine()

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    wav = synth.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
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

clips, scenes, t = [], [], 0.0
for sid, text, sub in SCRIPT:
    x = tts(text)
    sec = len(x) / SR
    dur = round(LEAD + sec + TAIL, 2)
    scenes.append({'id': sid, 'start': round(t, 2), 'dur': dur, 'speechStart': round(t + LEAD, 2),
                   'speechEnd': round(t + LEAD + sec, 2), 'sub': sub})
    clips.append((t + LEAD, x))
    print(f'{t:5.1f}s  {sid:10s} speech {sec:4.1f}s')
    t += dur
scenes.append({'id': 'outro', 'start': round(t, 2), 'dur': OUTRO, 'sub': ''})
TOTAL = round(t + OUTRO, 2)
print('total', TOTAL)

with open(os.path.join(HERE, 'timings.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成(ナレーションの実尺に合わせたシーン割り)\n')
    f.write('window.TIMINGS = ' + json.dumps({'total': TOTAL, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')

voice = np.zeros(int(TOTAL * SR), dtype=np.float32)
for st, x in clips:
    s = int(st * SR); voice[s:s + len(x)] += x[:len(voice) - s]
voice = voice / (np.max(np.abs(voice)) or 1) * 0.85

def _ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, s in enumerate(scenes[:-1], 1):
        f.write(f"{i}\n{_ts(s['speechStart'])} --> {_ts(s['speechEnd'] + 0.3)}\n{s['sub']}\n\n")

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, len(voice) - len(rms) * hop))
gain = 0.42 - (0.42 - 0.17) * np.clip(envl / 0.12, 0, 1)
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = voice + music * gain
# 効果音: タイトルで刃が落ちる瞬間(render.html の sTitle と同期)に「シュッ」+「ドン」
hit = scenes[0]['dur'] - 1.0 + 0.22
rng = np.random.default_rng(3)
n = int(0.25 * SR); tt = np.arange(n) / SR
swish = rng.standard_normal(n).astype(np.float32) * np.linspace(0, 1, n) ** 2 * 0.25
swish = np.convolve(swish, np.ones(8) / 8, mode='same')
n2 = int(0.9 * SR); t2 = np.arange(n2) / SR
thud = (np.sin(2 * np.pi * (55 + 60 * np.exp(-t2 * 25)) * t2) * np.exp(-t2 * 6)
        + 0.3 * rng.standard_normal(n2) * np.exp(-t2 * 40)).astype(np.float32) * 0.9
for st, x in ((hit - 0.25, swish), (hit, thud)):
    s0 = int(st * SR); mixed[s0:s0 + len(x)] += x[:len(mixed) - s0]
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)

def save(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', path)
save(os.path.join(OUT, 'narration.wav'), voice)
save(os.path.join(OUT, 'bgm.wav'), music)
save(os.path.join(OUT, 'mix.wav'), mixed)
