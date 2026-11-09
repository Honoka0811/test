# -*- coding: utf-8 -*-
"""script.js の原稿を VOICEVOX(四国めたん ノーマル)でチャンクごとに合成し、
シーン尺を音声の長さから決めて次の3つを書き出す。
  output/narration.wav  ナレーションのみ(48kHz モノラル)
  output/subtitles_ja.srt
  timing.js             render.html が読むタイムライン(シーン・字幕の開始/終了秒)
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
  SPEED          話速(既定 1.15)
"""
import os, io, json, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')
SR = 48000
SPEED = float(os.environ.get('SPEED', '1.15'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))

LEAD = 0.35         # シーン開始 → 最初の発話
GAP_CHUNK = 0.22    # 同じシーン内のチャンク間
TAIL = 0.45         # 最後の発話 → 次のシーン
FIRST_LEAD = 0.6    # 動画冒頭だけ少し長めに
END_HOLD = 2.2      # 最終シーンの発話後(クレジット表示)

SCRIPT = json.loads(subprocess.check_output(
    ['node', '-e', 'process.stdout.write(JSON.stringify(require(process.argv[1])))', os.path.join(HERE, 'script.js')]))

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', f'{VV}/open_jtalk_dic_utf_8-1.11')))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', f'{VV}/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
name = next(f'{c.name}/{st.name}' for c in synth.metas() for st in c.styles if st.id == STYLE)
print('engine: VOICEVOX', name, 'speed', SPEED)


def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.pitch_scale = 0.0
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]          # 前後の無音を詰める
    if len(idx):
        x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = min(400, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x


clips, scenes, cues = [], [], []
t = 0.0
for si, sc in enumerate(SCRIPT):
    start = t
    t += FIRST_LEAD if si == 0 else LEAD
    chunks = []
    for ci, (rd, sb) in enumerate(zip(sc['read'], sc['sub'])):
        if ci: t += GAP_CHUNK
        x = tts(rd)
        clips.append((t, x))
        d = len(x) / SR
        chunks.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': sb})
        cues.append((t, t + d, sb))
        t += d
    t += END_HOLD if si == len(SCRIPT) - 1 else TAIL
    scenes.append({'id': sc['id'], 'start': round(start, 3), 'dur': round(t - start, 3), 'chunks': chunks})
    print(f"{start:6.2f}s  {t - start:5.2f}s  {sc['id']}")
TOTAL = round(t, 2)
print('total', TOTAL)

track = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for st, x in clips:
    s = int(st * SR); track[s:s + len(x)] += x
track = track[:int(TOTAL * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

with open(os.path.join(HERE, 'timing.js'), 'w', encoding='utf-8') as f:
    f.write('// narrate.py が自動生成。手で編集しない\n')
    f.write('globalThis.TIMING = ' + json.dumps({'total': TOTAL, 'scenes': scenes}, ensure_ascii=False, indent=1) + ';\n')


def ts(x):
    ms = int(round(x * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, s) in enumerate(cues, 1):
        nxt = cues[i][0] if i < len(cues) else TOTAL
        f.write(f'{i}\n{ts(a)} --> {ts(min(b + 0.25, nxt))}\n{s}\n\n')
print('wrote narration.wav, subtitles_ja.srt, timing.js')
