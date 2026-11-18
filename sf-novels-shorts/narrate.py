# -*- coding: utf-8 -*-
"""scenes.json の原稿を VOICEVOX(四国めたん)で合成し、タイムライン・字幕・BGM入りミックスを書き出す。
映像の尺はナレーションの長さから決まる(音声が先、映像が後)。

出力:
  output/narration.wav   ナレーションのみ
  output/bgm.wav         BGM のみ
  output/mix.wav         ナレーション + BGM(発話中は BGM を自動で下げる)
  output/timeline.js     render.html が読むシーン開始/終了時刻
  output/subtitles_ja.srt

環境変数:
  VOICEVOX_ORT    libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS   0.vvm を置いたディレクトリ
  VOICEVOX_STYLE  スタイルID(既定 2 = 四国めたん ノーマル。0=あまあま 6=ツンツン 4=セクシー)
  VOICEVOX_SPEED  話速(既定 1.26)
"""
import os, io, json, wave, glob
import numpy as np
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)

SR = 48000
LEAD = 0.22     # シーン開始から声が出るまで
TAIL = 0.30     # 声が終わってから次のシーンまで
END_HOLD = 1.1  # 最後のカードを見せる余韻
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.26'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))

data = json.load(open(os.path.join(HERE, 'scenes.json'), encoding='utf-8'))
scenes = data['scenes']

# ---------- VOICEVOX ----------
import pyopenjtalk
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
dic = os.environ.get('VOICEVOX_DICT') or os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
if not os.path.isdir(dic):
    pyopenjtalk.g2p('あ')  # 辞書を自動ダウンロード
ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dic))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
name = next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == STYLE)
print('voice:', name, 'speed', SPEED)

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.25
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.05
    for p in q.accent_phrases:            # 読点の間を詰めてテンポよく
        pm = p.pause_mora
        if isinstance(pm, dict):
            pm['vowel_length'] = min(pm['vowel_length'], 0.28)
        elif pm is not None:
            pm.vowel_length = min(pm.vowel_length, 0.28)
    wav = synth.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return resample(x, sr), q.kana

# ---------- タイムライン ----------
t = 0.0
clips, timeline = [], []
for i, sc in enumerate(scenes):
    x, kana = tts(sc['say'])
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.85
    dur = LEAD + len(x) / SR + TAIL + (END_HOLD if i == len(scenes) - 1 else 0)
    dur = round(dur * 30) / 30            # フレーム境界に合わせる
    clips.append((t + LEAD, x))
    timeline.append({**{k: v for k, v in sc.items() if k != 'say'}, 'start': round(t, 4), 'end': round(t + dur, 4),
                     'voiceStart': round(t + LEAD, 4), 'voiceEnd': round(t + LEAD + len(x) / SR, 4)})
    print(f'{i:2d} {t:6.2f}s +{dur:5.2f}s  {kana}')
    t += dur
TOTAL = round(t, 4)
print('total', TOTAL)

track = np.zeros(int(TOTAL * SR) + 1, dtype=np.float32)
for start, x in clips:
    s = int(start * SR)
    track[s:s + len(x)] += x[:len(track) - s]

def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)

write_wav(os.path.join(OUT, 'narration.wav'), track)

with open(os.path.join(OUT, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps({'title': data['title'], 'total': TOTAL, 'voice': 'VOICEVOX:四国めたん',
                                               'scenes': timeline}, ensure_ascii=False, indent=1) + ';\n')

def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, sc in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(sc['voiceStart'])} --> {ts(min(sc['voiceEnd'] + 0.25, sc['end']))}\n{sc['sub'].replace('|', '')}\n\n")

# ---------- BGM をダッキングしながらミックス ----------
music = bgm_mod.generate(TOTAL)
music = np.pad(music, (0, max(0, len(track) - len(music))))[:len(track)]
write_wav(os.path.join(OUT, 'bgm.wav'), music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms):
    env[i] = max(v, (env[i - 1] if i else 0.0) * 0.88)
env = np.pad(np.repeat(env, hop), (0, len(track) - len(rms) * hop))
speech = np.clip(env / 0.1, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.42, 0.17
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)
