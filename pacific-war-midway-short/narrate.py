# -*- coding: utf-8 -*-
"""script.json の原稿を VOICEVOX(四国めたん)で 1 フレーズずつ合成し、
ナレーション音声(output/voice.wav)・タイムライン(output/timeline.json)・字幕(output/subtitles_ja.srt)を書き出す。
シーンの長さはナレーションの実際の長さから決まるので、無音の「間延び」が出ない。

環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたんは 0.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
  VOICE_SPEED    話速(既定 1.3)
"""
import os, io, json, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')
SR = 48000
SPEED = float(os.environ.get('VOICE_SPEED', '1.3'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
INTRO = 0.15      # 冒頭の無音(フック 1 語目をすぐ聞かせる)
CHUNK_GAP = 0.08  # 同じシーン内のフレーズ間
OUTRO = 1.6       # 最後のフレーズ後に残す余韻

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    os.path.join(VV, 'ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so')))
synth = Synthesizer(ort, OpenJtalk(os.environ.get('VOICEVOX_DICT', os.path.join(VV, 'open_jtalk_dic_utf_8-1.11'))))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', os.path.join(VV, 'vvms')), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)
speaker = next((c.name, st.name) for c in synth.metas() for st in c.styles if st.id == STYLE)
print('VOICEVOX:', '/'.join(speaker), 'speed', SPEED)

# 読みの補正(OpenJTalk が誤読しやすい語)
READ_FIX = {
    '米空母': 'べいくうぼ', '米雷撃機': 'べいらいげきき', '零戦': 'ゼロせん', '蒼龍': 'そうりゅう',
    '飛龍': 'ひりゅう', '赤城': 'あかぎ', '加賀': 'かが', '真水': 'まみず', '境に': 'さかいに',
    '日本': 'にほん',
}

def tts(text, speed):
    for k, v in READ_FIX.items():
        text = text.replace(k, v)
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = speed
    q.intonation_scale = 1.15   # 抑揚を少し強めて語りに張りを出す
    q.pre_phoneme_length = 0.0
    q.post_phoneme_length = 0.05
    wav = synth.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.006)[0]
    if len(idx):
        x = x[max(0, idx[0] - 240): idx[-1] + 1200]
    f = min(240, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x, q.kana

script = json.load(open(os.path.join(HERE, 'script.json'), encoding='utf-8'))
pieces, timeline = [], {'scenes': [], 'speaker': '四国めたん'}
t = INTRO
for si, sc in enumerate(script['scenes']):
    s_start = t
    chunks = []
    for ci, ch in enumerate(sc['chunks']):
        t += ch.get('pre', 0.0)
        x, kana = tts(ch.get('r', ch['t']), ch.get('speed', SPEED))
        d = len(x) / SR
        pieces.append((t, x))
        chunks.append({'t': ch['t'], 'hl': ch.get('hl', []), 'start': round(t, 3), 'end': round(t + d, 3)})
        print(f"{t:6.2f}s {d:4.2f}s  {ch['t']}\n           {kana}")
        t += d + (CHUNK_GAP if ci < len(sc['chunks']) - 1 else 0)
    t += sc.get('gap', 0.2)
    timeline['scenes'].append({'id': sc['id'], 'start': round(s_start, 3), 'end': round(t, 3), 'chunks': chunks})
total = t - script['scenes'][-1].get('gap', 0.2) + OUTRO
timeline['scenes'][-1]['end'] = round(total, 3)
timeline['duration'] = round(total, 3)

track = np.zeros(int(np.ceil(total * SR)), dtype=np.float32)
for st, x in pieces:
    s = int(st * SR); track[s:s + len(x)] += x[:len(track) - s]
track = track / (np.max(np.abs(track)) + 1e-9) * 0.9
with wave.open(os.path.join(OUT, 'voice.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
json.dump(timeline, open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def ts(v):
    return f'{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{int(v % 60):02d},{int(round((v % 1) * 1000)) % 1000:03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 0
    for sc in timeline['scenes']:
        for ch in sc['chunks']:
            i += 1
            f.write(f"{i}\n{ts(ch['start'])} --> {ts(ch['end'] + 0.15)}\n{ch['t']}\n\n")
print(f'total {total:.2f}s  -> output/voice.wav, timeline.json, subtitles_ja.srt')
