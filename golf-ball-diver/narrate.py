# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX(四国めたん ノーマル)で合成し、
字幕キュー(output/cues.json, output/subtitles_ja.srt)と、BGM をダッキングしたミックス音声(output/mix.wav)を書き出す。
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま、6 = ツンツン)
"""
import os, io, wave, glob, json
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
TOTAL = 53.0
LEAD = 0.4

# (開始秒, シーン長, 読み上げ原稿, 字幕)  render.html の SCENES と対応
SCRIPT = [
    (0, 6.5, 'ゴルフ場の池の底にもぐるお仕事、ゴルフボールダイバーって、ご存知かしら？',
             'ゴルフ場の池の底に潜るお仕事、ゴルフボールダイバーって、ご存知かしら？'),
    (6.5, 7.5, 'アメリカだけで、失われるゴルフボールは、年間およそ三億個。その多くが、池の底に沈んでいるの。',
               'アメリカだけで、失われるゴルフボールは年間およそ3億個。その多くが池の底に沈んでいるの。'),
    (14, 8.5, 'ダイバーはゴルフ場と契約して、閉場後の池に潜り、泥の中のボールを手探りで拾い集めるのよ。',
              'ダイバーはゴルフ場と契約して、閉場後の池に潜り、泥の中のボールを手探りで拾い集めるのよ。'),
    (22.5, 8.5, 'でも、水の中は泥で視界ほぼゼロ。冷たい水に、アメリカ南部では、ワニやヘビまで。まさに命がけね。',
                'でも、水の中は泥で視界ほぼゼロ。冷たい水に、アメリカ南部ではワニやヘビまで。まさに命がけね。'),
    (31, 8.5, '一日に数千個を回収することもあって、腕利きなら、年収一千万円を超える人もいるんですって。',
              '1日に数千個を回収することもあって、腕利きなら年収1,000万円を超える人もいるんですって。'),
    (39.5, 8, '集めたボールは、洗浄して、選別されて、ロストボールとして、もう一度お店に並ぶの。',
              '集めたボールは洗浄・選別されて、ロストボールとしてもう一度お店に並ぶの。'),
    (47.5, 5.5, '池ポチャのボールにも、第二の人生があるのね。',
                '池ポチャのボールにも、第二の人生があるのね。'),
]

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('engine: VOICEVOX', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def tts(text, speed):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = speed; q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    return x[max(0, idx[0] - 1200): idx[-1] + 2400] if len(idx) else x

track = np.zeros(int(TOTAL * SR), np.float32)
cues = []
for start, dur, text, sub in SCRIPT:
    limit = dur - LEAD - 0.3
    speed = 1.15
    for _ in range(6):
        x = tts(text, speed); sec = len(x) / SR
        if sec <= limit: break
        speed = min(speed * sec / limit * 1.02, 1.4)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {sub[:16]}…')
    f = min(600, len(x) // 4); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR); e = min(s + len(x), len(track))
    track[s:e] += x[:e - s]
    cues.append({'a': round(start + LEAD, 3), 'b': round(min(start + LEAD + sec + 0.25, start + dur - 0.05), 3), 'text': sub})

track = track / (np.max(np.abs(track)) or 1) * 0.85
def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
write_wav(os.path.join(OUT, 'narration.wav'), track)

json.dump(cues, open(os.path.join(OUT, 'cues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
def ts(t): return f'{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round((t % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{ts(c['a'])} --> {ts(c['b'])}\n{c['text']}\n\n")

# ---- BGM をダッキングしてミックス ----
music = bgm_mod.generate(TOTAL)[:len(track)]
write_wav(os.path.join(OUT, 'bgm.wav'), music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(track) - len(rms) * hop))
speech = np.clip(env / 0.12, 0, 1)
gain = 0.42 - (0.42 - 0.17) * speech
gain = np.convolve(gain, np.ones(SR // 10) / (SR // 10), mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)
print('wrote output/narration.wav, bgm.wav, mix.wav, cues.json, subtitles_ja.srt')
