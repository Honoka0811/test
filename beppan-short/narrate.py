# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:青山龍星)を合成し、字幕タイミング・BGM ミックスまで作る。
出力: output/narration.wav, output/timings.json, output/subtitles_ja.srt, output/bgm.wav, output/mix.wav
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT / VOICEVOX_STYLE(既定 13 = 青山龍星 ノーマル)
"""
import os, io, re, json, wave, glob
import numpy as np
from script import SCENES
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
SPEED = float(os.environ.get('NARRATION_SPEED', '1.30'))
LEAD, GAP, TAIL = 0.35, 0.45, 1.6   # 冒頭の間 / シーン間の間 / 最後の余韻(秒)

def dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    d = os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
    if not os.path.isdir(d): pyopenjtalk.g2p('あ')   # 初回は辞書を自動ダウンロード
    return d

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
    '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m: synth.load_voice_model(m)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))
print('voice:', next(c.name + '/' + s.name for c in synth.metas() for s in c.styles if s.id == STYLE))

def mora_len(m): return (m.consonant_length or 0.0) + m.vowel_length

def speak(chunks, style=None):
    style = style or STYLE
    """1 シーン分を 1 回で合成し、(波形, [(句の開始秒, 終了秒)]) を返す"""
    text = ''.join(c[1] for c in chunks)
    q = synth.create_audio_query(text, style)
    q.speed_scale = SPEED; q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.1
    q.intonation_scale = 1.1
    wav = synth.synthesis(q, style)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    # ポーズで区切られたグループごとの時間(クエリ上の長さ)
    groups, t, g0 = [], q.pre_phoneme_length, None
    for ap in q.accent_phrases:
        if g0 is None: g0 = t
        t += sum(mora_len(m) for m in ap.moras)
        if ap.pause_mora is not None:
            groups.append((g0, t)); pm = ap.pause_mora; t += pm['vowel_length'] if isinstance(pm, dict) else pm.vowel_length; g0 = None
    if g0 is not None: groups.append((g0, t))
    scale = (len(x) / sr) / (t + q.post_phoneme_length)   # 実際の波形長に合わせて補正
    groups = [(a * scale, b * scale) for a, b in groups]
    kana = ''.join(m.text for ap in q.accent_phrases for m in ap.moras)
    need = [len(re.findall('[、。]', c[1])) for c in chunks]
    spans = []
    if sum(need) == len(groups):
        i = 0
        for n in need:
            spans.append((groups[i][0], groups[i + n - 1][1])); i += n
    else:   # ポーズ数が合わない場合は文字数で按分
        print('  ! pause mismatch', sum(need), len(groups), '-> proportional')
        tot = sum(len(c[1]) for c in chunks); acc = 0; L = len(x) / sr
        for c in chunks:
            spans.append((L * acc / tot, L * (acc + len(c[1])) / tot)); acc += len(c[1])
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x, spans, kana

parts, scenes, t = [], [], LEAD
for sc in SCENES:
    sid, chunks = sc[0], sc[1]
    t += {'evidence': 0.35, 'end': 0.9}.get(sid, 0.0)   # 「ところが」の後と、結びの前に溜めを作る
    x, spans, kana = speak(chunks, sc[2] if len(sc) > 2 else None)
    print(f'{t:6.2f}s  {len(x) / SR:5.2f}s  {sid}: {kana}')
    f = 480; x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    parts.append((t, x))
    scenes.append({'id': sid, 'voice0': t, 'voice1': t + len(x) / SR,
                   'chunks': [{'t0': round(t + a, 3), 't1': round(t + b, 3), 'text': c[0], 'hl': c[2]}
                              for (a, b), c in zip(spans, chunks)]})
    t += len(x) / SR + GAP
TOTAL = round(t - GAP + TAIL, 2)
# シーン境界 = 前シーンの声の終わりと次シーンの声の始まりの中間
for i, s in enumerate(scenes):
    s['start'] = 0.0 if i == 0 else round((scenes[i - 1]['voice1'] + s['voice0']) / 2, 3)
for i, s in enumerate(scenes):
    s['end'] = TOTAL if i == len(scenes) - 1 else scenes[i + 1]['start']
print('total', TOTAL, 's')

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
for t0, x in parts:
    s = int(t0 * SR); track[s:s + len(x)] += x
track = track / np.max(np.abs(track)) * 0.85

def write_wav(name, x):
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', name)

write_wav('narration.wav', track)
json.dump({'fps': 30, 'duration': TOTAL, 'scenes': scenes}, open(os.path.join(OUT, 'timings.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

def ts(t):
    ms = int(round(t * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
flat = [c for s in scenes for c in s['chunks']]
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(flat):
        end = min(c['t1'] + 0.35, flat[i + 1]['t0'] - 0.02) if i + 1 < len(flat) else c['t1'] + 0.35
        f.write(f"{i + 1}\n{ts(c['t0'])} --> {ts(end)}\n{c['text']}\n\n")

# ---- BGM: ナレーション中は音量を下げる(ダッキング) ----
music = bgm_mod.generate(TOTAL, [s['start'] for s in scenes])
write_wav('bgm.wav', music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
env = np.zeros_like(rms)
for i, v in enumerate(rms): env[i] = max(v, (env[i - 1] if i else 0) * 0.9)
env = np.repeat(env, hop); env = np.pad(env, (0, len(track) - len(env)))
speech = np.clip(env / 0.1, 0, 1)
gain = 0.50 - (0.50 - 0.20) * speech
k = SR // 8; gain = np.convolve(gain, np.ones(k) / k, mode='same')
mix = track + music[:len(track)] * gain
write_wav('mix.wav', mix / max(1.0, np.max(np.abs(mix)) / 0.95))
