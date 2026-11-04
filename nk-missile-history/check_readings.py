# -*- coding: utf-8 -*-
"""読み間違いチェック: output/narration.wav を1文ずつ切り出して音声認識にかけ、字幕の原文・VOICEVOX の読み(カナ)と並べて表示する。
音声認識は sherpa-onnx の日本語モデル2種(ReazonSpeech zipformer / SenseVoice)。ASR_DIR でモデルの場所を指定(既定 /home/user/asr)。
"""
import os, re, json, wave, glob
import numpy as np
import sherpa_onnx

HERE = os.path.dirname(os.path.abspath(__file__))
ASR = os.environ.get('ASR_DIR', '/home/user/asr')
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')
z = f'{ASR}/sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01'
s = f'{ASR}/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17'
reazon = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f'{z}/encoder-epoch-99-avg-1.int8.onnx', decoder=f'{z}/decoder-epoch-99-avg-1.int8.onnx',
    joiner=f'{z}/joiner-epoch-99-avg-1.int8.onnx', tokens=f'{z}/tokens.txt', num_threads=4)
sense = sherpa_onnx.OfflineRecognizer.from_sense_voice(model=f'{s}/model.int8.onnx', tokens=f'{s}/tokens.txt', language='ja', use_itn=True, num_threads=4)

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
vv = Synthesizer(Onnxruntime.load_once(filename=f'{VV}/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'), OpenJtalk(f'{VV}/open_jtalk_dic_utf_8-1.11'))
for f in glob.glob(f'{VV}/vvms/*.vvm'):
    with VoiceModelFile.open(f) as m: vv.load_voice_model(m)

with wave.open(os.path.join(HERE, 'output', 'narration.wav')) as w:
    sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
x16 = np.interp(np.arange(0, len(x), sr / 16000), np.arange(len(x)), x).astype(np.float32)
tl = json.load(open(os.path.join(HERE, 'output', 'timeline.json'), encoding='utf-8'))
cfg = json.load(open(os.path.join(HERE, 'scenes.json'), encoding='utf-8'))
says = [l['say'] for sc in cfg['scenes'] for l in sc['lines']]
i = 0
for sc in tl['scenes']:
    for ln in sc['lines']:
        seg = x16[int((ln['start'] - 0.1) * 16000): int((ln['end'] + 0.15) * 16000)]
        out = []
        for rec in (reazon, sense):
            st = rec.create_stream(); st.accept_waveform(16000, seg); rec.decode_stream(st); out.append(st.result.text)
        print(f"[{i + 1:02d}] 原文  : {re.sub(r'\[\[|\]\]', '', ln['show'])}")
        print(f"     読み  : {vv.create_audio_query(says[i], 13).kana}")
        print(f"     認識A : {out[0]}")
        print(f"     認識B : {out[1]}\n")
        i += 1
