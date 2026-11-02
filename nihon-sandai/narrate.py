# -*- coding: utf-8 -*-
"""シーンごとのナレーション(男性音声)を合成し、BGM(bgm.py)をダッキングしながらミックスして動画に合成する。
既定は VOICEVOX(青山龍星)。voicevox_core が無い場合は Open JTalk にフォールバックする。
使い方: python3 narrate.py [入力mp4] [出力mp4]
環境変数:
  VOICEVOX_ORT   libvoicevox_onnxruntime.so のパス
  VOICEVOX_VVMS  *.vvm を置いたディレクトリ
  VOICEVOX_DICT  Open JTalk 辞書ディレクトリ(省略時は pyopenjtalk 同梱のもの)
  VOICEVOX_STYLE スタイルID(既定 13 = 青山龍星 ノーマル。11 = 玄野武宏 ノーマル)
"""
import sys, os, io, wave, glob, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'output', 'nihon_sandai.mp4')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'output', 'nihon_sandai_narrated.mp4')
WAV = os.path.join(HERE, 'output', 'narration.wav')
SRT = os.path.join(HERE, 'output', 'subtitles_ja.srt')

SR = 48000
T_TITLE, T_ITEM, T_END = 3.6, 5.3, 3.4   # render.html と対応
TOTAL = T_TITLE + T_ITEM * 10 + T_END     # 60.0
LEAD = 0.45  # シーン開始からナレーション開始までの間

# 読み上げ用原稿(固有名詞は読み間違い防止のため、かなで書いた箇所がある)
ITEM_SCRIPT = [
    'にほん三大まつり、ぎおんまつり、てんじんまつり、かんだまつり。',
    'にほんさんけい、まつしま、あまのはしだて、みやじま。',
    'にほんさんめいえん、けんろくえん、かいらくえん、こうらくえん。',
    'にほん三大やけい、北海道のはこだて、兵庫のこうべ、そして長崎。',
    'にほんさんめいじょう、なごやじょう、おおさかじょう、くまもとじょう。',
    'にほんさんめいせん、群馬のくさつ、岐阜のげろ、兵庫のありま。',
    'にほんさんめいばく、けごんのたき、なちのたき、ふくろだのたき。',
    'にほん三大ラーメン、札幌のみそ、きたかたのしょうゆ、博多のとんこつ。',
    'にほん三大わぎゅう、三重のまつさかぎゅう、兵庫のこうべぎゅう、滋賀のおうみぎゅう。',
    'にほん三大がっかりめいしょ、さっぽろとけいだい、はりまやばし、オランダざか。',
]
# 字幕用テキスト(画面表示向けの表記)
ITEM_SUB = [
    '日本三大祭り。祇園祭、天神祭、神田祭。',
    '日本三景。松島、天橋立、宮島。',
    '日本三名園。兼六園、偕楽園、後楽園。',
    '日本三大夜景。北海道の函館、兵庫の神戸、そして長崎。',
    '日本三名城。名古屋城、大阪城、熊本城。',
    '日本三名泉。群馬の草津、岐阜の下呂、兵庫の有馬。',
    '日本三名瀑。華厳の滝、那智の滝、袋田の滝。',
    '日本三大ラーメン。札幌の味噌、喜多方の醤油、博多のとんこつ。',
    '日本三大和牛。三重の松阪牛、兵庫の神戸牛、滋賀の近江牛。',
    '日本三大がっかり名所。札幌時計台、はりまや橋、オランダ坂。',
]
SCRIPT = [(0.0, T_TITLE, 'にほん三大まるまる、じゅうれんぱつ。言えますか?')]
SUBTITLES = ['日本三大○○、10連発。言えますか?']
for i, s in enumerate(ITEM_SCRIPT):
    SCRIPT.append((T_TITLE + i * T_ITEM, T_ITEM, s)); SUBTITLES.append(ITEM_SUB[i])
SCRIPT.append((T_TITLE + 10 * T_ITEM, T_END, '全部言えましたか?こたえはコメントで。'))
SUBTITLES.append('全部言えましたか?答えはコメントで。')

def _dict_dir():
    d = os.environ.get('VOICEVOX_DICT')
    if d: return d
    apt_dic = '/var/lib/mecab/dic/open-jtalk/naist-jdic'   # apt の open-jtalk-mecab-naist-jdic
    if os.path.isdir(apt_dic): return apt_dic
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
        self.style = int(os.environ.get('VOICEVOX_STYLE', '13'))
        name = next((c.name + '/' + st.name) for c in self.synth.metas() for st in c.styles if st.id == self.style)
        print('engine: VOICEVOX', name)
        self.max_speed = 1.3
        self.credit = 'VOICEVOX:' + name.split('/')[0]
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

class OpenJtalkCliEngine:
    """apt の open-jtalk(男性音声 nitech-jp-atr503-m001)を使うフォールバック"""
    DIC = os.environ.get('OPENJTALK_DIC', '/var/lib/mecab/dic/open-jtalk/naist-jdic')
    VOICE = os.environ.get('OPENJTALK_VOICE', '/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice')
    def __init__(self):
        import shutil, tempfile
        self.bin = shutil.which('open_jtalk')
        if not self.bin or not os.path.isdir(self.DIC) or not os.path.isfile(self.VOICE):
            raise RuntimeError('open_jtalk not installed')
        self.tmp = tempfile.mkdtemp()
        print('engine: Open JTalk CLI (fallback)', os.path.basename(self.VOICE))
        self.credit = 'Open JTalk'
        self.max_speed = 1.5
    def __call__(self, text, speed):
        txt = os.path.join(self.tmp, 'in.txt'); out = os.path.join(self.tmp, 'out.wav')
        with open(txt, 'w', encoding='utf-8') as f: f.write(text + '\n')
        subprocess.run([self.bin, '-x', self.DIC, '-m', self.VOICE, '-r', f'{speed:.2f}', '-fm', '-1.0',
                        '-jf', '0.5', '-a', '0.52', '-ow', out, txt], check=True)
        with wave.open(out) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

class OpenJtalkEngine:
    def __init__(self):
        import pyopenjtalk
        self.tts = pyopenjtalk.tts
        print('engine: Open JTalk (fallback)')
        self.credit = 'Open JTalk'
        self.max_speed = 1.5
    def __call__(self, text, speed):
        x, sr = self.tts(text, speed=speed, half_tone=-1.5)
        return x.astype(np.float32) / 32768.0, sr

engine = None
for Engine in (VoicevoxEngine, OpenJtalkCliEngine, OpenJtalkEngine):
    try:
        engine = Engine(); break
    except Exception as e:  # noqa
        print(f'{Engine.__name__} unavailable: {e}')
if engine is None:
    sys.exit('no TTS engine available')

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
    limit = dur - LEAD - 0.15
    speed = 1.15  # 基準速度(全シーンでペースを揃える)
    for _ in range(6):
        x = synth(text, speed)
        sec = len(x) / SR
        if sec <= limit:
            break
        speed = min(speed * (sec / limit) * 1.02, engine.max_speed)
    flag = '' if sec <= limit else '  ** 超過 **'
    print(f'{start:5.1f}s  {sec:4.1f}s / {limit:4.1f}s  speed={speed:.2f}  {text[:16]}…{flag}')
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
with open(os.path.join(HERE, 'output', 'credit.txt'), 'w', encoding='utf-8') as f:
    f.write(engine.credit + '\n')

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
BGM_SILENT, BGM_SPEECH = 0.42, 0.20   # 無音時 / 発話時の BGM ゲイン(線形)
gain = BGM_SILENT - (BGM_SILENT - BGM_SPEECH) * speech
k = SR // 10
gain = np.convolve(gain, np.ones(k) / k, mode='same')
mixed = track + music * gain
mixed = mixed / max(1.0, np.max(np.abs(mixed)) / 0.95)
MIX = os.path.join(HERE, 'output', 'mix.wav')
with wave.open(MIX, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mixed * 32767).astype(np.int16).tobytes())
with wave.open(os.path.join(HERE, 'output', 'bgm.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((music * 32767).astype(np.int16).tobytes())
print('wrote', MIX)

if not os.path.exists(SRC):
    print(f'{SRC} がまだ無いので音声のみ書き出しました。node capture.js の後にもう一度実行するか build.sh を使ってください。')
    sys.exit(0)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SRC, '-i', MIX,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', DST], check=True)
print('wrote', DST)
