# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:青山龍星)を合成し、音声の長さからシーンのタイムライン(timeline.json)を決める。
映像(render.html)は timeline.json を読んでシーン尺を合わせるので、原稿を変えても映像と音声がずれない。
使い方: python3 narrate.py
環境変数: VOICEVOX_ORT / VOICEVOX_VVMS / VOICEVOX_DICT (pacific-war-analysis/README.md 参照)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
SR = 48000
NORMAL, HOT = 13, 81  # 青山龍星 ノーマル / 熱血

# id, スタイル, 読み上げ原稿, 字幕(画面表示用), 前の間(秒), 後ろの間(秒)
SCRIPT = [
    ('hook', HOT, '一生モノの革靴、どれを選ぶ？',
     '一生モノの革靴、どれを選ぶ？', 0.15, 0.15),
    ('intro', NORMAL, '世界の革靴ブランド、トップテンを一気に紹介します。',
     '世界の革靴ブランドTOP10を一気に紹介！', 0.0, 0.25),
    ('r10', NORMAL, '第十位、リーガル。にほんじんの足に合う木型で、本格グッドイヤー製法が手頃に。',
     '日本人の足に合う木型。本格グッドイヤー製法が手頃に', 0.2, 0.25),
    ('r9', NORMAL, '第九位、パラブーツ。自社製のラバーソールで雨にも強い、休日の名品です。',
     '自社製ラバーソールで雨にも強い、休日の名品', 0.2, 0.25),
    ('r8', NORMAL, '第八位、サントーニ。職人の手染めによるグラデーションが美しい、イタリアの色気。',
     '手染めのグラデーションが美しい、イタリアの色気', 0.2, 0.25),
    ('r7', NORMAL, '第七位、オールデン。コードバンの深い艶は、アメリカントラッドの象徴です。',
     'コードバンの深い艶は、アメトラの象徴', 0.2, 0.25),
    ('r6', NORMAL, '第六位、ジェイエムウエストン。自社のタンナーの革で作る、一生モノのローファー。',
     '自社タンナーの革で作る、一生モノのローファー', 0.2, 0.25),
    ('r5', NORMAL, '第五位、クロケットアンドジョーンズ。ジェームズ・ボンドも履いた、コスパ最強の英国靴。',
     '007も履いた、コスパ最強の英国靴', 0.2, 0.25),
    ('r4', NORMAL, '第四位、チャーチ。百五十年の歴史を持つ、英国紳士靴の王道です。',
     '150年の歴史を持つ、英国紳士靴の王道', 0.2, 0.25),
    ('r3', HOT, 'いよいよトップスリー！第三位、ベルルッティ。独自の染色、パティーヌが生む芸術的な色。',
     '独自の染色「パティーヌ」が生む芸術的な色', 0.25, 0.25),
    ('r2', NORMAL, '第二位、エドワードグリーン。職人の手仕上げが生む、英国靴の最高傑作。',
     '職人の手仕上げが生む、英国靴の最高傑作', 0.2, 0.3),
    ('tease', HOT, 'そして、堂々の第一位は……',
     'そして、堂々の第1位は…', 0.1, 0.9),
    ('r1', HOT, 'ジョンロブ！キング・オブ・シューズと呼ばれる、革靴の最高峰です。',
     '「キング・オブ・シューズ」と呼ばれる革靴の最高峰', 0.0, 0.35),
    ('outro', NORMAL, '最初の一足なら、黒のストレートチップが万能。保存して、靴選びの参考にしてください。',
     '最初の一足なら「黒のストレートチップ」が万能！', 0.2, 1.3),
]
SPEED = {'hook': 1.15, 'tease': 1.0, 'r1': 1.12}
DEFAULT_SPEED = 1.3


def dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')


from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.environ.get(
    'VOICEVOX_ORT', '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(dict_dir()))
for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
    with VoiceModelFile.open(f) as m:
        synth.load_voice_model(m)


def tts(text, style, speed):
    q = synth.create_audio_query(text, style)
    q.speed_scale = speed
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.02
    q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, style))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 600): idx[-1] + 1800]
    f = min(400, len(x) // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x


clips, scenes, t = [], [], 0.0
for sid, style, text, sub, pre, post in SCRIPT:
    x = tts(text, style, SPEED.get(sid, DEFAULT_SPEED))
    dur = pre + len(x) / SR + post
    scenes.append({'id': sid, 'start': round(t, 3), 'dur': round(dur, 3),
                   'voice': [round(t + pre, 3), round(t + pre + len(x) / SR, 3)], 'sub': sub})
    clips.append((t + pre, x))
    print(f'{sid:6s} {t:5.2f}s +{dur:4.2f}s  {text[:20]}')
    t += dur

TOTAL = round(t, 3)
track = np.zeros(int(TOTAL * SR) + 1, dtype=np.float32)
for s, x in clips:
    i = int(s * SR); track[i:i + len(x)] += x[:len(track) - i]
track = track / (np.max(np.abs(track)) + 1e-9) * 0.9
os.makedirs(OUT, exist_ok=True)
with wave.open(os.path.join(OUT, 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
with open(os.path.join(HERE, 'timeline.json'), 'w', encoding='utf-8') as f:
    json.dump({'total': TOTAL, 'scenes': scenes}, f, ensure_ascii=False, indent=1)
print(f'total {TOTAL:.2f}s -> output/narration.wav, timeline.json')
