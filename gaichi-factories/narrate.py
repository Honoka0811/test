# -*- coding: utf-8 -*-
"""ナレーション(VOICEVOX:四国めたん)を1文ずつ合成し、次を書き出す。
  output/narration.wav   ナレーション音声(48kHz mono)
  data/timeline.js       各文・各字幕チャンクの開始/終了時刻(render.html が読む)
  output/subtitles_ja.srt
動画の尺はナレーションの長さから決まる(映像側がナレーションに追従する)。
環境変数:
  VOICEVOX_DIR   setup.sh が VOICEVOX 一式を置いたディレクトリ(既定: ./vendor/voicevox)
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル)
"""
import os, io, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VV = os.environ.get('VOICEVOX_DIR', os.path.join(HERE, 'vendor', 'voicevox'))
STYLE = int(os.environ.get('VOICEVOX_STYLE', '2'))
SR = 48000
SPEED = 1.12
LEAD = 0.7         # 冒頭の間
GAP_LINE = 0.22    # 文と文の間
GAP_SCENE = 0.85   # シーンが変わるときの間(カメラ移動の時間)
TAIL = 2.6         # 最後の余韻(クレジット表示)

# (id, シーン, 読み上げ用テキスト, 字幕チャンク[...])
# 読みを誤る固有名詞は読み上げ用テキスト側だけカタカナにしてある
LINES = [
    ('i1', 'intro', '戦前、日本の大企業は、海の向こうにも巨大な工場を持っていました。',
        ['戦前、日本の大企業は', '海の向こうにも\n巨大な工場を持っていました']),
    ('i2', 'intro', '朝鮮、満洲、台湾、樺太。地図で見ていきましょう。',
        ['朝鮮、満洲、台湾、樺太', '地図で見ていきましょう']),
    ('k1', 'chosen', 'まずは朝鮮。', ['まずは朝鮮']),
    ('k2', 'chosen', '興南には、日本窒素肥料が、東洋一といわれた化学コンビナートを建設。',
        ['興南には、日本窒素肥料が', '東洋一といわれた\n化学コンビナートを建設']),
    ('k3', 'chosen', 'オウリョッコウの、スイホウダムなど、巨大な水力発電とセットでした。',
        ['鴨緑江の水豊ダムなど', '巨大な水力発電と\nセットでした']),
    ('k4', 'chosen', 'ケンジホと清津には、日本製鉄の製鉄所。',
        ['兼二浦と清津には\n日本製鉄の製鉄所']),
    ('k5', 'chosen', '京城には、鐘紡などの紡績工場もありました。',
        ['京城には、鐘紡などの\n紡績工場もありました']),
    ('m1', 'manshu', '続いて満洲。', ['続いて満洲']),
    ('m2', 'manshu', '鞍山には、満鉄が始めた製鉄所、のちの昭和製鋼所。',
        ['鞍山には\n満鉄が始めた製鉄所', 'のちの昭和製鋼所']),
    ('m3', 'manshu', 'ブジュンには、巨大な露天掘りの炭鉱。',
        ['撫順には\n巨大な露天掘りの炭鉱']),
    ('m4', 'manshu', '新京には、日産コンツェルンが本社ごと移転し、満洲重工業開発が生まれました。',
        ['新京には、日産コンツェルンが\n本社ごと移転し', '満洲重工業開発が\n生まれました']),
    ('t1', 'taiwan', '南の台湾は、砂糖の島。', ['南の台湾は、砂糖の島']),
    ('t2', 'taiwan', '台湾製糖や明治製糖などの工場が、各地に並びました。',
        ['台湾製糖や明治製糖などの\n工場が、各地に並びました']),
    ('t3', 'taiwan', '高雄には、日月潭の電力を使うアルミ工場や、浅野セメントの工場も。',
        ['高雄には、日月潭の電力を使う\nアルミ工場や', '浅野セメントの工場も']),
    ('s1', 'karafuto', '北の樺太は、王子製紙の独壇場。', ['北の樺太は\n王子製紙の独壇場']),
    ('s2', 'karafuto', '豊原、マオカ、エストルなど、島じゅうにパルプ工場がありました。',
        ['豊原、真岡、恵須取など', '島じゅうに\nパルプ工場がありました']),
    ('o1', 'outro', 'しかし千九百四十五年、敗戦ですべてを失います。',
        ['しかし1945年\n敗戦ですべてを失います']),
    ('o2', 'outro', '残された工場やダムの一部は、戦後も現地の産業を支えました。',
        ['残された工場やダムの一部は', '戦後も\n現地の産業を支えました']),
]

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ort = Onnxruntime.load_once(filename=os.path.join(VV, 'voicevox_onnxruntime-linux-x64-1.17.3', 'lib', 'libvoicevox_onnxruntime.so'))
synth = Synthesizer(ort, OpenJtalk(os.path.join(VV, 'open_jtalk_dic_utf_8-1.11')))
with VoiceModelFile.open(os.path.join(VV, '0.vvm')) as m:
    synth.load_voice_model(m)
print('voice:', next(c.name + '/' + st.name for c in synth.metas() for st in c.styles if st.id == STYLE))

def tts(text):
    q = synth.create_audio_query(text, STYLE)
    q.speed_scale = SPEED
    q.intonation_scale = 1.15
    q.pre_phoneme_length = 0.05
    q.post_phoneme_length = 0.05
    with wave.open(io.BytesIO(synth.synthesis(q, STYLE))) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    idx = np.where(np.abs(x) > 0.004)[0]
    x = x[max(0, idx[0] - 960): idx[-1] + 1920]
    f = 480
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    return x, q.kana

t = LEAD
clips, timeline, prev_scene = [], [], None
for lid, scene, text, chunks in LINES:
    if prev_scene is not None:
        t += GAP_SCENE if scene != prev_scene else GAP_LINE
    x, kana = tts(text)
    dur = len(x) / SR
    # 字幕チャンクの時間配分は文字数に比例
    w = np.array([len(c.replace('\n', '')) + 2 for c in chunks], dtype=float)
    edges = t + np.concatenate([[0], np.cumsum(w) / w.sum()]) * dur
    timeline.append({'id': lid, 'scene': scene, 'start': round(t, 3), 'end': round(t + dur, 3),
                     'chunks': [{'text': c, 'start': round(float(a), 3), 'end': round(float(b), 3)}
                                for c, a, b in zip(chunks, edges[:-1], edges[1:])]})
    clips.append((t, x))
    print(f'{t:6.2f}s {dur:5.2f}s {lid} {kana}')
    t += dur
    prev_scene = scene
total = round(t + TAIL, 2)

track = np.zeros(int(total * SR), dtype=np.float32)
for start, x in clips:
    s = int(start * SR)
    track[s:s + len(x)] += x
track = track / np.max(np.abs(track)) * 0.85

os.makedirs(os.path.join(HERE, 'output'), exist_ok=True)
with wave.open(os.path.join(HERE, 'output', 'narration.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
with open(os.path.join(HERE, 'data', 'timeline.js'), 'w', encoding='utf-8') as f:
    f.write('window.TIMELINE=' + json.dumps({'duration': total, 'lines': timeline}, ensure_ascii=False, indent=1) + ';\n')

def ts(v):
    ms = int(round(v * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
with open(os.path.join(HERE, 'output', 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    i = 0
    for ln in timeline:
        for c in ln['chunks']:
            i += 1
            f.write(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n\n")
print('total', total, 's')
