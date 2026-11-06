# -*- coding: utf-8 -*-
"""シーンごとのナレーション(四国めたん)を合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
既定は VOICEVOX(四国めたん ノーマル, style 2)。voicevox_core が無い場合は Open JTalk にフォールバックする。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ(0.vvm に四国めたんが含まれる)
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ
  VOICEVOX_STYLE スタイルID(既定 2 = 四国めたん ノーマル。0 = あまあま, 6 = ツンツン, 4 = セクシー)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'prewar_weapon_patents.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'prewar_weapon_patents_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')

SR = 48000
TOTAL = 116.5
LEAD = 0.45  # シーン開始からナレーション開始までの間

# (開始秒, シーン長, 原稿)  render.html の SCENES と対応
SCRIPT = [
    (0, 8.5, '戦前の日本では、兵器にかかわる発明が、特許としてどう扱われていたのでしょうか。今回はその歴史を、数字でたどります。'),
    (8.5, 13.5, '日本の特許制度は、千八百八十五年の専売特許条例から始まりました。特許第一号は、ほったずいしょうのさび止め塗料。鉄の船底を守るこの発明は、海軍の軍艦にも採用されました。'),
    (22, 17.5, '軍事上秘密とされた発明を公開しない、秘密特許という制度もありました。指定するのは陸軍大臣と海軍大臣。審査官のおよそ二割は、陸海軍の技術将校でした。件数は明治に二十四件、大正に百十六件、昭和には千四百三十二件へ急増します。'),
    (39.5, 16.5, '一方、主力兵器の多くは海外の特許に頼っていました。零戦の二十ミリ機銃は、スイス・エリコン社のライセンス。三式戦闘機のエンジンはドイツのダイムラー・ベンツ製で、陸軍系の川崎と海軍系の愛知が、別々にライセンスを取得しました。'),
    (56, 18.5, '逆に、日本発の発明が生かされなかった例もあります。やぎひでつぐと宇田新太郎のアンテナは、千九百二十六年に特許となりましたが、日本軍は重視しませんでした。千九百四十二年、シンガポールで押収した英軍のレーダー資料に「ヤギ」の名があった、という逸話が残っています。'),
    (74.5, 15, '材料の特許も、兵器を支えました。千九百三十五年、海軍の要請で住友金属の五十嵐勇が開発したちょうちょうジュラルミンは、一年以内に特許出願され、零戦の主翼の桁に使われて、機体を軽くしました。'),
    (89.5, 15.5, '戦時には、敵国の特許そのものが標的になりました。千九百十七年の工業所有権戦時法で、敵国民の特許は効力を失い、ドイツ発の医薬品などが国内で作られます。この法律は、千九百四十二年に再び発動されました。'),
    (105, 11.5, '秘密特許と戦時法は、千九百四十八年、戦争放棄をうたう新憲法のもとで廃止されました。発明を守る制度は、戦争とともに、形を変えてきたのです。'),
]

# 字幕用テキスト(読み上げ用の漢数字ではなく、画面表示向けの表記)
SUBTITLES = [
    '戦前の日本では、兵器にかかわる発明が、特許としてどう扱われていたのでしょうか。今回はその歴史を、数字でたどります。',
    '日本の特許制度は、1885年の専売特許条例から始まりました。特許第1号は、堀田瑞松のさび止め塗料。鉄の船底を守るこの発明は、海軍の軍艦にも採用されました。',
    '軍事上秘密とされた発明を公開しない、秘密特許という制度もありました。指定するのは陸軍大臣と海軍大臣。審査官のおよそ2割は、陸海軍の技術将校でした。件数は明治に24件、大正に116件、昭和には1,432件へ急増します。',
    '一方、主力兵器の多くは海外の特許に頼っていました。零戦の20mm機銃は、スイス・エリコン社のライセンス。三式戦闘機のエンジンはドイツのダイムラー・ベンツ製で、陸軍系の川崎と海軍系の愛知が、別々にライセンスを取得しました。',
    '逆に、日本発の発明が生かされなかった例もあります。八木秀次と宇田新太郎のアンテナは、1926年に特許となりましたが、日本軍は重視しませんでした。1942年、シンガポールで押収した英軍のレーダー資料に「YAGI」の名があった、という逸話が残っています。',
    '材料の特許も、兵器を支えました。1935年、海軍の要請で住友金属の五十嵐勇が開発した超々ジュラルミンは、1年以内に特許出願され、零戦の主翼の桁に使われて、機体を軽くしました。',
    '戦時には、敵国の特許そのものが標的になりました。1917年の工業所有権戦時法で、敵国民の特許は効力を失い、ドイツ発の医薬品などが国内で作られます。この法律は、1942年に再び発動されました。',
    '秘密特許と戦時法は、1948年、戦争放棄をうたう新憲法のもとで廃止されました。発明を守る制度は、戦争とともに、形を変えてきたのです。',
]
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    cand = '/home/user/vv/dict/open_jtalk_dic_utf_8-1.11'
    if os.path.isdir(cand): return cand
    import pyopenjtalk
    return os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')

class VoicevoxEngine:
    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT',
            '/home/user/vv/ort/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so'))
        self.synth = Synthesizer(ort, OpenJtalk(_dict_dir()))
        for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', '/home/user/vv/vvms'), '*.vvm'))):
            with VoiceModelFile.open(f) as m:
                self.synth.load_voice_model(m)
        self.style = int(os.environ.get('VOICEVOX_STYLE', '2'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
    def __call__(self, text, speed):
        q = self.synth.create_audio_query(text, self.style)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.1
        wav = self.synth.synthesis(q, self.style)
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback)')
    def __call__(self, text, speed):
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

def synth(text, speed):
    x, sr = engine(text, speed)
    x = resample(x, sr)
    idx = np.where(np.abs(x) > 0.004)[0]
    if len(idx):
        x = x[max(0, idx[0] - 1200): idx[-1] + 2400]
    return x

track = np.zeros(int(TOTAL * SR), dtype=np.float32)
cues = []
for li, (start, dur, text) in enumerate(SCRIPT):
    limit = dur - LEAD - 0.35
    speed = 1.2  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, 1.35)
    flag = '' if sec <= limit else '  ** OVER **'
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:18]}…{flag}')
    n = len(x); f = min(600, n // 4)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    s = int((start + LEAD) * SR)
    e = min(s + n, len(track))
    track[s:e] += x[:e - s]
    cues.append((start + LEAD, start + LEAD + n / SR, SUBTITLES[li]))

peak = np.max(np.abs(track)) or 1
track = track / peak * 0.85
with wave.open(WAV, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((track * 32767).astype(np.int16).tobytes())
print('wrote', WAV)

def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec - int(sec)) * 1000)):03d}'
with open(SRT, 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{_ts(a)} --> {_ts(min(b + 0.3, TOTAL))}\n{t}\n\n')
print('wrote', SRT)

# ---------- BGM をダッキングしながらミックス ----------
import bgm as bgm_mod
music = bgm_mod.generate(TOTAL)
music = music[:len(track)] if len(music) >= len(track) else np.pad(music, (0, len(track) - len(music)))
hop = SR // 20
rms = np.sqrt(np.mean(track[:len(track) // hop * hop].reshape(-1, hop) ** 2, axis=1))
envl = np.zeros_like(rms)
for i, v in enumerate(rms):
    prev = envl[i - 1] if i else 0.0
    envl[i] = max(v, prev * 0.9)       # リリース ≈ 0.5 秒
envl = np.repeat(envl, hop); envl = np.pad(envl, (0, len(track) - len(envl)))
speech = np.clip(envl / 0.12, 0, 1)
BGM_SILENT, BGM_SPEECH = 0.40, 0.17   # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(HERE, 'output', 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

if os.environ.get('NARRATE_ONLY'):
    sys.exit(0)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
