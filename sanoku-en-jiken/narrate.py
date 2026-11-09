# -*- coding: utf-8 -*-
"""シーンごとのナレーションを VOICEVOX(四国めたん)で合成し、字幕タイミング(cues.json / SRT)と
BGM(bgm.py)をダッキングしたミックス音声(output/mix.wav)を書き出す。
映像は capture.js が cues.json を読んで字幕を焼き込み、最後に make.sh が音声と合成する。
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(四国めたん: ノーマル=0.vvm, ささやき=5.vvm)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
"""
import os, io, wave, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output'); os.makedirs(OUT, exist_ok=True)
SR = 48000
TOTAL = 68.0
LEAD = 0.5

# 四国めたんのスタイルID: 2=ノーマル, 4=セクシー, 36=ささやき, 37=ヒソヒソ
NORMAL, WHISPER = 2, 36

# (開始秒, シーン長, スタイル, 読み上げ原稿, 字幕)  render.html の SCENES と対応
SCRIPT = [
    (0.0, 7.5, NORMAL,
     '千九百六十八年、東京。誰ひとり傷つけることなく、三億円が消えた。',
     '1968年、東京。誰ひとり傷つけることなく、3億円が消えた。'),
    (7.5, 8.5, NORMAL,
     '十二月十日、朝九時二十分ごろ。雨の府中。工場のボーナス、約三億円を積んだ現金輸送車が走っていた。',
     '12月10日、朝9時20分ごろ。雨の府中。工場のボーナス、約3億円を積んだ現金輸送車が走っていた。'),
    (16.0, 8.0, NORMAL,
     'そこへ、一台の白バイが追いついてくる。警官は言った。この車に、ダイナマイトが仕掛けられている。',
     'そこへ、一台の白バイが追いついてくる。警官は言った。「この車に、ダイナマイトが仕掛けられている」'),
    (24.0, 8.0, NORMAL,
     '男は車の下に潜り込み、煙が噴き出す。爆発するぞ。行員たちが逃げた隙に、男は車ごと走り去った。',
     '男は車の下に潜り込み、煙が噴き出す。「爆発するぞ!」行員たちが逃げた隙に、男は車ごと走り去った。'),
    (32.0, 8.0, NORMAL,
     '白バイは偽物。煙は発煙筒。奪われた現金は、二億九千四百三十万七千五百円。',
     '白バイは偽物。煙は発煙筒。奪われた現金は、2億9430万7500円。'),
    (40.0, 9.0, NORMAL,
     '現場には、百二十点を超える遺留品。捜査員は延べ十七万人。容疑者は、十一万人以上にのぼった。',
     '現場には、120点を超える遺留品。捜査員は延べ17万人。容疑者は、11万人以上にのぼった。'),
    (49.0, 8.0, NORMAL,
     'それでも、犯人にはたどり着けなかった。千九百七十五年十二月十日、時効成立。',
     'それでも、犯人にはたどり着けなかった。1975年12月10日、時効成立。'),
    (57.0, 7.5, WHISPER,
     'あの白バイの男は、今もどこかで、生きているのかもしれない。',
     'あの白バイの男は、今もどこかで、生きているのかもしれない。'),
]
HITS = (0.25, 32.0, 49.0, 57.0)   # インパクト音のタイミング
HEART = ((24.0, 31.6),)           # 心音を鳴らす区間

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    name = 'VOICEVOX'
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        names = {st.id: c.name + '/' + st.name for c in self.synth.metas() for st in c.styles}
        print('engine: VOICEVOX', names[NORMAL], '/', names.get(WHISPER))
    def __call__(self, text, style, speed):
        q = self.synth.create_audio_query(text, style)
        q.speed_scale = speed
        q.pitch_scale = -0.02 if style == NORMAL else 0.0   # 少し低めに落ち着かせる
        q.intonation_scale = 0.9
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    """VOICEVOX が使えない環境用の仮ナレーション(四国めたんではない)"""
    name = 'OpenJTalk'
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback / 仮ナレーション)')
    def __call__(self, text, style, speed):
        x, sr = self.tts(text, speed=speed)
        return x.astype(np.float32) / 32768.0, sr

try:
    engine = VoicevoxEngine()
except Exception as e:  # noqa
    print('VOICEVOX unavailable:', e)
    engine = OpenJtalkEngine()

def resample(x, sr):
    if sr == SR: return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def synth(text, style, speed):
    x, sr = engine(text, style, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for start, dur, style, text, sub in SCRIPT:
    limit = dur - LEAD - 0.4
    speed = 1.05 if style == NORMAL else 0.95
    for _ in range(6):
        x = synth(text, style, speed)
        sec = len(x) / SR
        if sec <= limit: break
        speed = min(speed * (sec / limit) * 1.02, 1.35)
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    if style == WHISPER: x *= 1.6   # ささやきは音量が小さいので持ち上げる
    s = int((start + LEAD) * SR); e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append({'start': round(start + LEAD, 3), 'end': round(start + LEAD + n / SR, 3), 'text': sub})

track = track / (np.max(np.abs(track)) or 1) * 0.85
def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print('wrote', path)
write_wav(os.path.join(OUT, 'narration.wav'), track)

with open(os.path.join(OUT, 'cues.json'), 'w', encoding='utf-8') as f:
    json.dump({'engine': engine.name, 'cues': cues}, f, ensure_ascii=False, indent=1)
def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{_ts(c['start'])} --> {_ts(min(c['end'] + 0.3, TOTAL))}\n{c['text']}\n\n")
print('wrote cues.json / subtitles_ja.srt')

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL, hits=HITS, heart=HEART)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
write_wav(os.path.join(OUT, 'bgm.wav'), music)
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    envl[i] = max(v, (envl[i - 1] if i else 0.0) * 0.9)
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.32, 0.11
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
write_wav(os.path.join(OUT, 'mix.wav'), mixed)
