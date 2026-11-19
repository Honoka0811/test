"""VOICEVOX Core（四国めたん ノーマル）で各シーンのナレーションを生成する。
usage: python3 tts.py <voicevox_dir> <out_dir>
"""
import json
import os
import sys
import wave

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SCENES  # noqa: E402

METAN_NORMAL = 2

vv, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
ort = Onnxruntime.load_once(
    filename=f"{vv}/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so.1.17.3")
syn = Synthesizer(ort, OpenJtalk(f"{vv}/open_jtalk_dic_utf_8-1.11"))
with VoiceModelFile.open(f"{vv}/0.vvm") as m:
    syn.load_voice_model(m)

durs = []
for i, s in enumerate(SCENES):
    q = syn.create_audio_query(s["yomi"], METAN_NORMAL)
    q.speed_scale = 1.28          # ショート動画向けに少し速め
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.1
    q.output_sampling_rate = 48000
    print(q.kana)
    wav = syn.synthesis(q, METAN_NORMAL)
    path = f"{out}/n{i:02d}.wav"
    with open(path, "wb") as f:
        f.write(wav)
    with wave.open(path) as w:
        d = w.getnframes() / w.getframerate()
    durs.append(d)
    print(i, f"{d:.2f}s", s["yomi"])

json.dump(durs, open(f"{out}/durations.json", "w"))
print("total", sum(durs))
