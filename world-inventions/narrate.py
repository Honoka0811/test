# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を合成し、その長さからシーンの尺を決めて timeline.js を書き出す。
あわせて BGM(bgm.py)をダッキングしながらミックスし output/mix.wav を作る。
出力: output/narration.wav, output/mix.wav, output/subtitles_ja.srt, timeline.js
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン)
  VOICE_SPEED    話速(既定 1.3)
"""
import os, io, sys, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from script import INTRO, ITEMS, OUTRO
import bgm as bgm_mod

OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('VOICE_SPEED', '1.3'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
LEAD = 0.35   # シーン開始 → 発話開始
TAIL = 0.35   # 発話終了 → 次のシーン
END_HOLD = 1.6  # 最後のシーンの余韻


def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d:
        return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')


from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
voice_name = next(c.name + '(' + st.name + ')' for c in synth.metas() for st in c.styles if st.id == STYLE)
print('voice:', voice_name, 'speed', SPEED)


def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 600): idx[-1] + 2400]
    f = min(480, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x


segments = [dict(type='intro', **INTRO)] + [dict(type='item', **it) for it in ITEMS] + [dict(type='outro', **OUTRO)]
clips, t = [], 0.0
for i, sg in enumerate(segments):
    x = tts(sg['read'])
    sec = len(x) / SR
    dur = LEAD + sec + TAIL + (END_HOLD if i == len(segments) - 1 else 0)
    sg.update(start=round(t, 3), dur=round(dur, 3), say0=round(t + LEAD, 3), say1=round(t + LEAD + sec, 3))
    clips.append((t + LEAD, x))
    print(f'{t:5.1f}s  {sec:4.1f}s  {sg["sub"][:20]}…')
    t += dur
TOTAL = round(t, 3)

voice = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for st, x in clips:
    s = int(st * SR); voice[s:s + len(x)] += x
voice = voice[:int(TOTAL * SR)]
voice = voice / (np.max(np.abs(voice)) or 1) * 0.85


def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)


write_wav(os.path.join(OUT, 'narration.wav'), voice)

# ---------- timeline.js(render.html が読む) ----------
timeline = dict(total=TOTAL, voice=voice_name,
                scenes=[{k: v for k, v in sg.items() if k != 'read'} for sg in segments])
with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成(手で編集しない)\nwindow.TIMELINE = ' +
            json.dumps(timeline, ensure_ascii=False, indent=1) + ';\n')
print('wrote timeline.js  total', TOTAL, 's')


# ---------- 字幕 SRT ----------
def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'


with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, sg in enumerate(segments, 1):
        f.write(f'{i}\n{ts(sg["say0"])} --> {ts(min(sg["say1"] + 0.3, TOTAL))}\n{sg["sub"]}\n\n')

# ---------- BGM をダッキングしてミックス ----------
music = bgm_mod.generate(TOTAL)
music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]
hop = SR // 20
rms = np.sqrt(np.mean(voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.pad(np.repeat(env, hop), (0, len(voice) - len(rms) * hop))
speech = np.clip(env / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.17
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
write_wav(os.path.join(OUT, 'bgm.wav'), music)
mixed = voice + music * gain
write_wav(os.path.join(OUT, 'mix.wav'), mixed / max(1.0, np.max(np.abs(mixed)) / 0.95))
