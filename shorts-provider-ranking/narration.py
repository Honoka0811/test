"""四国めたん（VOICEVOX）でナレーションを生成し、各セリフの長さを timeline.json に書き出す"""
import json, wave, io, sys
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

VV = sys.argv[1]  # VOICEVOX 素材ディレクトリ
# (シーンID, 読み上げテキスト, スタイルID)  2=ノーマル 6=ツンツン 0=あまあま
LINES = [
    ("hook1", "ちょっと！夜になるとネットが遅い、なんて思ってない？", 6),
    ("hook2", "それ、回線選びで損してるかもしれないわよ。", 2),
    ("intro", "快適にネットができる光回線、ランキングで紹介するわ！", 2),
    ("r5", "第5位、楽天ひかり、えんひかりなど。とにかく安さ重視ならコレ。アイピーブイシックス対応で夜も安定よ。", 2),
    ("r4", "第4位、ソフトバンク光。ソフトバンクやワイモバイルを使ってるなら、セット割でお得ね。", 2),
    ("r3", "第3位、ドコモ光。対応エリアが広くて、ドコモやアハモのユーザーにおすすめよ。", 2),
    ("r2", "第2位、エーユーひかり。独自回線だから、夜でも速度が落ちにくいの。", 2),
    ("drum", "そして、栄えある第1位は……", 2),
    ("r1", "ニューロ光！実際の速度はトップクラス。ゲームをするなら、これ一択よ！", 6),
    ("tips", "選ぶコツは3つ。住んでる場所で使えるか、スマホとのセット割、そしてアイピーブイシックス対応か。", 2),
    ("cta", "保存して、回線選びの参考にしてね。フォローもよろしくね！", 0),
]
SPEED = {"hook1": 1.2, "drum": 1.0}
GAP_AFTER = {"drum": 1.1, "hook2": 0.15}

ort = Onnxruntime.load_once(filename=f"{VV}/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so.1.17.3")
syn = Synthesizer(ort, OpenJtalk(f"{VV}/open_jtalk_dic_utf_8-1.11"))
with VoiceModelFile.open(f"{VV}/0.vvm") as m:
    syn.load_voice_model(m)

t = 0.35
out = []
for sid, text, style in LINES:
    q = syn.create_audio_query(text, style)
    q.speed_scale = SPEED.get(sid, 1.15)
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.05
    q.output_sampling_rate = 48000
    wav = syn.synthesis(q, style)
    open(f"build/{sid}.wav", "wb").write(wav)
    with wave.open(io.BytesIO(wav)) as w:
        dur = w.getnframes() / w.getframerate()
    out.append({"id": sid, "start": round(t, 3), "dur": round(dur, 3)})
    t += dur + GAP_AFTER.get(sid, 0.25)
json.dump({"scenes": out, "total": round(t + 0.8, 3)}, open("build/timeline.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False), t)
