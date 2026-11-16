# -*- coding: utf-8 -*-
"""script.json を VOICEVOX(四国めたん)で合成し、ナレーション音声とタイムラインを書き出す。

出力:
  output/narration.wav   ナレーションのみ(48kHz mono)
  timeline.js            render.html が読むタイムライン(window.TIMELINE)
  output/subtitles_ja.srt
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, re, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
SPEED = 1.18          # 話速
INTONATION = 1.15     # 抑揚
LEAD_IN = 0.6         # 冒頭の無音
GAP_LINE = 0.22       # 文と文の間
GAP_SCENE = 0.75      # シーンの変わり目
TAIL = 4.2            # 最後の文のあと(クレジット表示)

import pyopenjtalk
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT') or
    glob.glob('/home/user/vv/ort/*/lib/libvoicevox_onnxruntime.so')[0])
dic = os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
if not os.path.isdir(dic):
    pyopenjtalk.g2p('あ')  # 辞書を自動ダウンロード
synth = Synthesizer(ort, OpenJtalk(dic))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
print('voice:', next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == STYLE))

def plain(s):
    return re.sub(r'[\[\]/]', '', s)

def mora_count(s):
    k = pyopenjtalk.g2p(plain(s), kana=True)
    k = re.sub(r'[、。「」\s]', '', k)
    return max(1, len(re.sub(r'[ャュョァィゥェォヮ]', '', k)))

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def speak(read_chunks):
    """文を 1 回で合成し、(波形, 各チャンクの終了時刻[秒]) を返す"""
    text = ''.join(read_chunks)
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = INTONATION
    q.pre_phoneme_length = 0.0
    q.post_phoneme_length = 0.0
    # モーラごとの長さ(ポーズ含む)
    durs = []  # (秒, is_pause)
    for ap in q.accent_phrases:
        for m in ap.moras:
            durs.append(((m.consonant_length or 0) + m.vowel_length, False))
        if ap.pause_mora is not None:
            pm = ap.pause_mora
            durs.append((pm['vowel_length'] if isinstance(pm, dict) else pm.vowel_length, True))
    wav = synth.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    x = resample(x, sr)
    total = len(x) / SR
    spoken = [d for d, p in durs if not p]
    scale = total / (sum(d for d, _ in durs) or 1)
    # チャンク境界 = 累積モーラ数(比例配分)。境界直後がポーズならポーズの終わりまで含める
    counts = [mora_count(c) for c in read_chunks]
    ratio = len(spoken) / sum(counts)
    ends, acc, idx, t = [], 0.0, 0, 0.0
    seq = durs
    pos = 0  # seq 上の位置
    done_moras = 0
    for ci, c in enumerate(counts):
        acc += c * ratio
        target = len(spoken) if ci == len(counts) - 1 else int(round(acc))
        while pos < len(seq) and done_moras < target:
            t += seq[pos][0]
            if not seq[pos][1]: done_moras += 1
            pos += 1
        cut = t
        if pos < len(seq) and seq[pos][1]:
            cut = t + seq[pos][0] * 0.5
        ends.append(min(total, cut * scale))
    ends[-1] = total
    return x, ends

script = json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))
t = LEAD_IN
pieces, lines = [], []
for i, e in enumerate(script):
    disp = e['text'].split('/')
    read = (e.get('read') or e['text']).split('/')
    read = [re.sub(r'[\[\]]', '', r) for r in read]
    assert len(disp) == len(read), (i, disp, read)
    x, ends = speak(read)
    f = 240
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    if i and script[i - 1]['scene'] != e['scene']:
        t += GAP_SCENE - GAP_LINE
    chunks, a = [], 0.0
    for d, b in zip(disp, ends):
        chunks.append({'text': d, 't0': round(t + a, 3), 't1': round(t + b, 3)})
        a = b
    lines.append({'i': i, 'scene': e['scene'], 't0': round(t, 3), 't1': round(t + len(x) / SR, 3), 'chunks': chunks})
    pieces.append((t, x))
    print(f'{t:6.2f}  {len(x) / SR:5.2f}s  {plain(e["text"])[:28]}')
    t += len(x) / SR + GAP_LINE
total = round(t - GAP_LINE + TAIL, 2)

track = np.zeros(int(total * SR) + SR, dtype=np.float32)
for t0, x in pieces:
    s = int(t0 * SR); track[s:s + len(x)] += x
track = track[:int(total * SR)]
track = track / (np.max(np.abs(track)) or 1) * 0.85
os.makedirs(OUT, exist_ok=True)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

scenes = []
for ln in lines:
    if not scenes or scenes[-1]['id'] != ln['scene']:
        scenes.append({'id': ln['scene'], 't0': ln['t0'], 'first': ln['i']})
for k, s in enumerate(scenes):
    s['t0'] = 0.0 if k == 0 else round(s['t0'] - GAP_SCENE * 0.5, 3)
    s['t1'] = total if k == len(scenes) - 1 else round(scenes[k + 1]['t0'] - GAP_SCENE * 0.5, 3)
tl = {'duration': total, 'fps': 30, 'lines': lines, 'scenes': scenes}
with open(os.path.join(HERE, 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')

def ts(v):
    ms = int(round(v * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for n, ln in enumerate(lines, 1):
        end = min(ln['t1'] + 0.15, lines[n]['t0'] if n < len(lines) else total)
        f.write(f"{n}\n{ts(ln['t0'])} --> {ts(end)}\n{plain(script[ln['i']]['text'])}\n\n")
print('total', total, 'sec')
