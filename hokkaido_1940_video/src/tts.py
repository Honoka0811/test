import sys, json, wave
sys.path.insert(0, "/tmp/claude-0/-home-user-test/6d1dd308-8d3d-5d9e-bb71-763cdc5e0fc0/scratchpad/work")
from lines import LINES
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
V="/tmp/claude-0/-home-user-test/6d1dd308-8d3d-5d9e-bb71-763cdc5e0fc0/scratchpad/vv"
ort=Onnxruntime.load_once(filename=V+"/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so.1.17.3")
syn=Synthesizer(ort, OpenJtalk(V+"/open_jtalk_dic_utf_8-1.11"))
with VoiceModelFile.open(V+"/0.vvm") as m: syn.load_voice_model(m)
SID=2  # 四国めたん ノーマル
durs={}
for key, text, _ in LINES:
    q=syn.create_audio_query(text, SID)
    q.speed_scale=1.25; q.intonation_scale=1.15; q.pre_phoneme_length=0.05; q.post_phoneme_length=0.1
    print(key, q.kana if hasattr(q,'kana') else '')
    wav=syn.synthesis(q, SID)
    open(f"voice_{key}.wav","wb").write(wav)
    with wave.open(f"voice_{key}.wav") as w: durs[key]=w.getnframes()/w.getframerate()
json.dump(durs, open("durs.json","w"), indent=1); print(durs)
