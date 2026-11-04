# -*- coding: utf-8 -*-
"""ショート動画用ナレーション(VOICEVOX: 青山龍星)。文ごとに合成し、
output/timing.json, subtitles_ja.srt, narration.wav, mix.wav(BGM込み) を書き出す。
使い方: python3 narrate.py   (環境変数は ../midway-analysis/narrate.py と同じ)
"""
import os, io, json, wave, glob, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'midway-analysis'))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.25'))
LEAD, TAIL, GAP = 0.3, 0.35, 0.16
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))

# (シーンID, 見出し, [(読み上げ文, 字幕文), ...])
SCENES = [
    ('hook', '空母4隻喪失', [
        ('千九百四十二年六月、ミッドウェー。日本海軍は主力空母四隻を、一度に失った。', '1942年6月、ミッドウェー。日本海軍は主力空母4隻を一度に失った。'),
        ('でも、勝ち筋はあった。', 'でも、勝ち筋はあった。'),
    ]),
    ('code', '① 暗号を更新しろ', [
        ('一つ目、暗号を更新しろ。', '①　暗号を更新しろ。'),
        ('アメリカは日本の暗号を解読し、攻撃目標を事前に知っていた。', 'アメリカは日本の暗号を解読し、攻撃目標を事前に知っていた。'),
        ('暗号書の更新が間に合っていれば、待ち伏せ自体が成立しない。', '暗号書の更新が間に合っていれば、待ち伏せ自体が成立しない。'),
    ]),
    ('concentrate', '② 戦力を分散するな', [
        ('二つ目、戦力を分散するな。', '②　戦力を分散するな。'),
        ('同じ日にアリューシャンも攻め、戦艦部隊は空母の数百キロ後ろ。決戦場には空母四隻だけ。', '同じ日にアリューシャンも攻め、戦艦部隊は空母の数百キロ後ろ。決戦場には空母4隻だけ。'),
        ('まとめて来ていれば、防空も索敵も倍だ。', 'まとめて来ていれば、防空も索敵も倍だ。'),
    ]),
    ('launch', '③ 積み替えるな、今すぐ飛ばせ', [
        ('三つ目、積み替えるな、今すぐ飛ばせ。', '③　積み替えるな、今すぐ飛ばせ。'),
        ('米空母発見の報で、南雲司令部は爆弾を魚雷に積み替えさせた。', '米空母発見の報で、南雲司令部は爆弾を魚雷に積み替えさせた。'),
        ('山口多聞は、そのまま出せ、と進言。', '山口多聞は「そのまま出せ」と進言。'),
        ('無視された結果、十時二十分、米急降下爆撃機が甲板を直撃。', '無視された結果、10時20分、米急降下爆撃機が甲板を直撃。'),
        ('たった五分で、三隻が炎上。', 'たった5分で、3隻が炎上。'),
    ]),
    ('cap', 'おまけ：頭上を空にするな', [
        ('さらに、護衛の零戦は低空の雷撃機に釣られて、頭上はがら空きだった。', 'さらに、護衛の零戦は低空の雷撃機に釣られて、頭上はがら空きだった。'),
    ]),
    ('war', 'でも、戦争には勝てない', [
        ('ただし。この日勝っても、アメリカは新型空母を十隻以上建造中。', 'ただし。この日勝っても、アメリカは新型空母を10隻以上建造中。'),
        ('反攻が一年遅れるだけで、国力の差は埋まらない。', '反攻が1年遅れるだけで、国力の差は埋まらない。'),
    ]),
    ('end', '', [
        ('勝てたのは、戦いだけ。戦争じゃない。', '勝てたのは「戦い」だけ。「戦争」じゃない。'),
    ]),
]

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', '/home/user/vv/dict/open_jtalk_dic_utf_8-1.11')))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/dl'), '*.vvm'))):
            with VoiceModelFile.open(f) as m: self.synth.load_voice_model(m)
        print('engine: VOICEVOX', next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == STYLE))
    def __call__(self, text):
        q = self.synth.create_audio_query(text, STYLE)
        q.speed_scale = SPEED; q.pre_phoneme_length = 0.04; q.post_phoneme_length = 0.06
        if os.environ.get('SHOW_KANA'): print('   ', q.kana)
        wav = self.synth.synthesis(q, STYLE)
        with wave.open(io.BytesIO(wav)) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0, w.getframerate()

engine = VoicevoxEngine()

def synth(text):
    x, sr = engine(text)
    if sr != SR:
        n = int(len(x) * SR / sr); x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx): x = x[max(0, idx[0] - 500): idx[-1] + 1500]
    f = min(400, len(x) // 4); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x

clips = []; timing = {'fps': 30, 'scenes': []}; t = 0.0
for sid, title, sents in SCENES:
    sc_start = t; t += LEAD; subs = []
    for spoken, shown in sents:
        x = synth(spoken); dur = len(x) / SR
        clips.append((t, x)); subs.append({'start': round(t, 3), 'end': round(t + dur, 3), 'text': shown}); t += dur + GAP
    t += TAIL - GAP
    timing['scenes'].append({'id': sid, 'title': title, 'start': round(sc_start, 3), 'dur': round(t - sc_start, 3), 'subs': subs})
    print(f'{sc_start:5.1f}s  {t - sc_start:4.1f}s  {title}')
TOTAL = round(t + 0.5, 2); timing['duration'] = TOTAL
timing['scenes'][-1]['dur'] = round(TOTAL - timing['scenes'][-1]['start'], 3)
print('total', TOTAL, 's')

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for start, x in clips:
    s = int(start * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]; track = track / (np.max(np.abs(track)) or 1) * 0.85

def wwav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
wwav(os.path.join(OUT, 'narration.wav'), track)
json.dump(timing, open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
def _ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 1
    for sc in timing['scenes']:
        for sb in sc['subs']: f.write(f"{i}\n{_ts(sb['start'])} --> {_ts(min(sb['end'] + 0.25, TOTAL))}\n{sb['text']}\n\n"); i += 1

import bgm as bgm_mod
music = bgm_mod.generate(TOTAL + 2)[:len(track)]; music = np.pad(music, (0, max(0, len(track) - len(music))))
fo = int(1.5 * SR); music[-fo:] *= np.linspace(1, 0, fo)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms): envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
gain = 0.42 - (0.42 - 0.17) * speech; k = SR // 10; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain; mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
wwav(os.path.join(OUT, 'mix.wav'), mixed)
print('wrote output/narration.wav output/timing.json output/subtitles_ja.srt output/mix.wav')
