# -*- coding: utf-8 -*-
"""ナレーション合成(VOICEVOX:青山龍星) → タイムライン / 字幕SRT / BGM付きミックス を output/ に書き出す。

  python3 narrate.py            # 音声・timeline.json・SRT・mix.wav を生成
  VOICEVOX_STYLE=81 python3 narrate.py   # スタイル変更(81=熱血, 84=しっとり)

必要な環境変数(VOICEVOX CORE 0.16 のファイル置き場):
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  15.vvm(青山龍星)を置いたディレクトリ
  VOICEVOX_DICT  open_jtalk_dic_utf_8-1.11 のディレクトリ
"""
import json, os, sys, wave, io
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
STYLE = int(os.environ.get('VOICEVOX_STYLE', '13'))   # 13 = 青山龍星 ノーマル
SPEED = float(os.environ.get('VOICEVOX_SPEED', '1.15'))
LEAD, PAD = 0.4, 0.7      # シーン頭の無音 / シーン末尾の余白(秒)
SR = 48000                # 書き出しサンプルレート(BGM と揃える)

VV = os.path.join(HERE, 'voicevox')
ORT = os.environ.get('VOICEVOX_ORT', os.path.join(VV, 'onnxruntime', 'lib', 'libvoicevox_onnxruntime.so'))
VVMS = os.environ.get('VOICEVOX_VVMS', os.path.join(VV, 'models'))
DICT = os.environ.get('VOICEVOX_DICT', os.path.join(VV, 'open_jtalk_dic_utf_8-1.11'))

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
syn = Synthesizer(Onnxruntime.load_once(filename=ORT), OpenJtalk(DICT))
with VoiceModelFile.open(os.path.join(VVMS, '15.vvm')) as m:
    syn.load_voice_model(m)

lines = json.load(open(os.path.join(HERE, 'narration.json'), encoding='utf-8'))
subs = json.load(open(os.path.join(HERE, 'subtitles.json'), encoding='utf-8'))

# ---------- 合成 ----------
clips = []
for i, text in enumerate(lines):
    q = syn.create_audio_query(text, STYLE)
    q.speed_scale = SPEED; q.pre_phoneme_length = 0.1; q.post_phoneme_length = 0.3
    wav = syn.synthesis(q, STYLE)
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
    # 24kHz → 48kHz(線形補間)
    x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x).astype(np.float32)
    clips.append(x); print(f'scene {i+1}: {len(x)/SR:.2f}s')

# ---------- タイムライン ----------
sc = []; t = 0.0
for x in clips:
    e = round(t + LEAD + len(x) / SR + PAD, 2); sc.append([round(t, 2), e]); t = e
TOTAL = sc[-1][1]
json.dump({'sc': sc, 'lead': LEAD}, open(os.path.join(HERE, 'timeline.json'), 'w'))
print('timeline', sc, 'total', TOTAL)

# ---------- ナレーショントラック ----------
track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for i, ((s, e), x) in enumerate(zip(sc, clips)):
    a = int((s + LEAD) * SR); b = min(a + len(x), len(track)); track[a:b] += x[:b - a]
    cues.append((s + LEAD, s + LEAD + len(x) / SR, subs[i]))
track = track / (np.max(np.abs(track)) or 1) * 0.85

def save(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
save(os.path.join(OUT, 'narration.wav'), track)

def _ts(t):
    m = int(t // 60); s = t % 60
    return f'00:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, txt) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{txt}\n\n')

# ---------- BGM(自作・権利フリー)をダッキングしてミックス ----------
sys.path.insert(0, os.path.join(HERE, '..', 'pacific-war-analysis'))
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
save(os.path.join(OUT, 'bgm.wav'), music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.pad(np.repeat(envl, hop), (0, len(track) - len(rms) * hop))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.40, 0.18
gain = np.convolve(BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech, np.ones(SR // 10) / (SR // 10), mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
save(os.path.join(OUT, 'mix.wav'), mixed)
print('wrote output/narration.wav output/bgm.wav output/mix.wav output/subtitles_ja.srt')
