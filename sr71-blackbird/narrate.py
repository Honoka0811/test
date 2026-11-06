# -*- coding: utf-8 -*-
"""script.py の原稿を VOICEVOX(四国めたん)で読み上げ、タイムラインを決める。
出力:
  output/narration.wav   ナレーションのみ(48kHz mono)
  output/timeline.json   シーン/字幕チャンクの開始・終了時刻(render.html と mix.py が使う)
  output/subtitles_ja.srt
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, glob, json, wave
import numpy as np
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
VV = '/home/user/vv'
SR = 48000

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

# シーンごとの話速(冒頭は溜めて、中盤はテンポよく)
SPEED = {'hook': 1.12, 'ending': 1.15}
DEFAULT_SPEED = 1.24
GAP_CHUNK = 0.12   # 同一シーン内のチャンク間
GAP_SCENE = 0.30   # シーン切り替え時の間(ここで効果音とカットが入る)
LEAD = 0.35        # 動画冒頭の無音
TAIL = 1.6         # 最後のチャンク後の余韻(エンドカード)
DRAMA = {('ending', 1): 0.55}  # 「ゼロ」の前だけ長めに溜める
CHUNK_SPEED = {('ending', 1): 0.85}  # 「ゼロ」はゆっくり言い切る


def tts(text, speed):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = speed
    q.intonation_scale = 1.25
    q.pitch_scale = 0.01
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.01)[0]
    x = x[max(0, idx[0] - 480): idx[-1] + 1440]
    f = 240
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x


clips, timeline = [], {'scenes': []}
t = LEAD
for si, (sid, chunks) in enumerate(SCENES):
    if si:
        t += GAP_SCENE
    scene = {'id': sid, 'start': round(t - (LEAD if si == 0 else GAP_SCENE / 2), 3), 'chunks': []}
    for ci, (disp, read, hl) in enumerate(chunks):
        if ci:
            t += GAP_CHUNK + DRAMA.get((sid, ci), 0)
        x = tts(read, CHUNK_SPEED.get((sid, ci), SPEED.get(sid, DEFAULT_SPEED)))
        clips.append((t, x))
        d = len(x) / SR
        scene['chunks'].append({'text': disp, 'hl': hl, 'start': round(t, 3), 'end': round(t + d, 3)})
        print(f'{t:6.2f}s  {d:4.2f}s  {disp}')
        t += d
    timeline['scenes'].append(scene)
total = t + TAIL
for i, s in enumerate(timeline['scenes']):
    s['end'] = timeline['scenes'][i + 1]['start'] if i + 1 < len(timeline['scenes']) else round(total, 3)
timeline['duration'] = round(total, 3)

track = np.zeros(int(total * SR) + 1, dtype=np.float32)
for st, x in clips:
    s = int(st * SR); track[s:s + len(x)] += x
track *= 0.9 / (np.max(np.abs(track)) + 1e-9)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump(timeline, f, ensure_ascii=False, indent=1)


def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    n = 0
    for s in timeline['scenes']:
        for c in s['chunks']:
            n += 1
            f.write(f"{n}\n{ts(c['start'])} --> {ts(c['end'] + 0.1)}\n{c['text'].replace('|', '')}\n\n")
print(f'total {total:.2f}s  -> output/narration.wav, timeline.json, subtitles_ja.srt')
