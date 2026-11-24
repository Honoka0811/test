# -*- coding: utf-8 -*-
"""「七つ目」(学校の七不思議 × コックリさん)の音声トラックを作る。

1) 台本 TIMELINE を VOICEVOX(四国めたん)で読み上げ、全イベントの時刻を確定する
2) 効果音・環境音を numpy / scipy だけで合成する(外部音源なし・権利フリー)
3) ミックスしてラウドネスを整え、映像側が使うタイムラインと字幕を書き出す

出力: output/mix.wav, output/narration.wav, output/timeline.json, output/subtitles_ja.srt
環境変数: VV_HOME (既定 /home/user/vv) … setup.sh が VOICEVOX 一式を置く場所
"""
import os, io, json, wave, glob, hashlib, subprocess
import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'output')
CACHE = os.path.join(OUT, 'voice_cache')
os.makedirs(CACHE, exist_ok=True)
VV = os.environ.get('VV_HOME', '/home/user/vv')
SR = 48000
FPS = 30
VOICE_LUFS = -16.5      # ナレーションのラウドネス(全体はスケア等で少し上がる)
VREF = -18.0            # ミックス内でのナレーション短期音量(dBFS)。以下はこれに対する相対 dB
VOICE_REL = {'N': 0.0, 'Q': -0.5, 'H': -1.0, 'G': 1.5, 'C': -0.5, 'CF': -1.5}
SFX_REL = {'knock_wood': -1.0, 'knock_soft': -7.0, 'knock_glass': -3.5, 'knock_door': 0.5, 'title_hit': 2.0,
           'knock_slide': -0.5, 'coin': -4.0, 'chalk': -9.0, 'chalk_snap': -6.0, 'chime': -11.0, 'crow': -15.0,
           'dread_hit': -1.0, 'thunder': 0.0, 'heartbeat': -7.0, 'riser': 1.0, 'scare': 8.5}
BED_REL = {'drone': -13.0, 'high': -30.0, 'room': -24.0, 'wind': -14.0, 'hum': -24.0, 'tinnitus': -34.0}

# ---------------------------------------------------------------- 声
# 四国めたん: ノーマル=2 / セクシー=4 / ささやき=36 / ヒソヒソ=37
VOICES = {
    'N': dict(style=2, speed=1.12, pitch=-0.02, inton=0.85, pause=1.15),   # 語り
    'Q': dict(style=2, speed=0.98, pitch=-0.05, inton=0.55, pause=1.3),   # 管理人の台詞(抑揚を消して淡々と)
    'H': dict(style=37, speed=1.0, pitch=0.0, inton=1.0, pause=1.25),     # ヒソヒソ
    'G': dict(style=36, speed=0.95, pitch=0.0, inton=0.9, pause=1.5),     # ささやき → 加工して「何か」の声に
    # コックリさんを唱える3人(全員四国めたん。声の高さとスタイルを変えて重ねる)
    'C1': dict(style=37, speed=1.0, pitch=0.0, inton=0.8, pause=1.2),    # ヒソヒソ
    'C2': dict(style=37, speed=1.0, pitch=0.07, inton=0.8, pause=1.2),   # ヒソヒソ(少し高く)
    'C3': dict(style=36, speed=1.0, pitch=-0.05, inton=0.8, pause=1.2),  # ささやき(少し低く)
}

# ---------------------------------------------------------------- 台本
# ('scene', 名前)                     映像シーンの切り替え
# ('gap', 秒)                         間
# ('say', 声, 読み上げ文[, 字幕])       ナレーション(長さぶん時間が進む)
# ('sfx', 名前, 進める秒[, 引数])        効果音
# ('mark', 名前)                      映像用の目印
TIMELINE = [
    ('scene', 'hall'),
    ('sfx', 'chime', 0.0),
    ('gap', 0.35),
    ('say', 'N', 'うちの学校の七不思議には、七つ目がありません。'),
    ('gap', 0.4),
    ('scene', 'title'),
    ('sfx', 'title_hit', 1.9),
    ('scene', 'board'),
    ('sfx', 'chalk', 0.15, {'lines': 7, 'step': 0.62, 'len': 0.5}),   # 黒板に 一〜六 と「七、」を書く
    ('say', 'N', '六つまでは、誰でも知っています。'),
    ('gap', 0.35),
    ('say', 'N', 'でも、七つ目を知った人は、いなくなるんです。'),
    ('sfx', 'chalk_snap', 0.55),
    ('scene', 'sheet'),
    ('sfx', 'crow', 0.0),
    ('gap', 0.25),
    ('say', 'N', 'だから放課後、コックリさんに聞いてみたんです。'),
    ('gap', 0.35),
    ('say', 'C', 'コックリさん、コックリさん。七つ目を、教えてください。', '「コックリさん、コックリさん。七つ目を教えてください」'),
    ('gap', 0.35),
    ('say', 'N', '十円玉が、ゆっくり、動きはじめました。'),
    ('gap', 0.2),
    ('sfx', 'coin', 2.85, {'path': [['い', 0.0, 0.8], ['れ', 1.05, 1.95], ['て', 2.2, 2.85]]}),
    ('gap', 0.75),
    ('scene', 'classdoor'),
    ('sfx', 'knock_slide', 1.5, {'hits': [0.0, 0.45, 0.9]}),
    ('say', 'N', '教室の戸を、誰かが、三回叩いたんです。'),
    ('gap', 0.4),
    ('scene', 'sheet2'),
    ('gap', 0.2),
    ('say', 'N', '慌てて、お帰りくださいと言うと、十円玉は。', '慌てて「お帰りください」と言うと、十円玉は……'),
    ('gap', 0.15),
    ('sfx', 'coin', 0.75, {'path': [['いいえ', 0.0, 0.75]]}),
    ('sfx', 'dread_hit', 1.5),
    ('scene', 'window'),
    ('gap', 0.3),
    ('say', 'N', 'その夜から、私の部屋の窓が、毎晩、叩かれます。'),
    ('gap', 0.3),
    ('sfx', 'knock_glass', 1.9, {'hits': [0.0, 0.45, 0.92]}),
    ('gap', 0.2),
    ('scene', 'clock'),
    ('gap', 0.35),
    ('say', 'N', 'そして今夜、四時四十四分。'),
    ('gap', 0.4),
    ('mark', 'clock_flip'),
    ('gap', 0.85),
    ('say', 'N', 'ノックが、ありません。'),
    ('gap', 0.5),
    ('scene', 'dark'),
    ('gap', 0.3),
    ('say', 'N', 'ノックって、入っていいか、たずねるためのもの、ですよね。',
     'ノックって、「入っていいか」たずねるためのもの、ですよね。'),
    ('gap', 0.5),
    ('say', 'N', 'でも、あの日、私たちは最初に、こう言ったんです。'),
    ('gap', 0.25),
    ('scene', 'flash'),
    ('gap', 0.15),
    ('say', 'CF', 'コックリさん、コックリさん、おいでください。', '「コックリさん、コックリさん、おいでください」'),
    ('gap', 0.1),
    ('sfx', 'coin', 1.0, {'path': [['はい', 0.0, 0.8]], 'reset': True}),
    ('scene', 'black'),
    ('gap', 0.8),
    ('say', 'G', 'だから、きたよ。', 'だから、来たよ'),
    ('gap', 0.08),
    ('scene', 'scare'),
    ('sfx', 'scare', 1.35),
    ('scene', 'outro'),
    ('gap', 0.9),
    ('say', 'H', '七つ目、知ってしまいましたね。'),
    ('gap', 0.5),
    ('sfx', 'knock_soft', 1.55, {'hits': [0.0, 0.46, 0.93]}),
    ('gap', 0.25),
]


# ---------------------------------------------------------------- VOICEVOX
class Voicevox:
    def __init__(self):
        import pyopenjtalk
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        ort = Onnxruntime.load_once(filename=glob.glob(os.path.join(VV, 'ort', '*', 'lib', 'libvoicevox_onnxruntime.so'))[0])
        dic = os.environ.get('VOICEVOX_DICT') or os.path.join(os.path.dirname(pyopenjtalk.__file__), 'open_jtalk_dic_utf_8-1.11')
        if not os.path.isdir(dic):
            pyopenjtalk.g2p('辞書')  # 初回は pyopenjtalk が辞書を取得する
        self.s = Synthesizer(ort, OpenJtalk(dic))
        for f in ('0.vvm', '5.vvm'):
            with VoiceModelFile.open(os.path.join(VV, 'vvms', f)) as m:
                self.s.load_voice_model(m)

    def __call__(self, text, v):
        q = self.s.create_audio_query(text, v['style'])
        q.speed_scale = v['speed']; q.pitch_scale = v['pitch']; q.intonation_scale = v['inton']
        q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.2
        for ap in q.accent_phrases:   # 読点の間を伸ばす(版によって dict / dataclass の両方がある)
            pm = ap['pause_mora'] if isinstance(ap, dict) else ap.pause_mora
            if pm is None: continue
            if isinstance(pm, dict): pm['vowel_length'] *= v['pause']
            else: pm.vowel_length *= v['pause']
        wav = self.s.synthesis(q, v['style'])
        with wave.open(io.BytesIO(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
        return signal.resample_poly(x, SR, sr) if sr != SR else x


_vv = None
def speak(key, text):
    """キャッシュ付きで合成し、前後の無音を詰めて返す"""
    global _vv
    v = VOICES[key]
    h = hashlib.sha1(json.dumps([text, v], ensure_ascii=False).encode()).hexdigest()[:16]
    path = os.path.join(CACHE, h + '.npy')
    if os.path.exists(path):
        x = np.load(path)
    else:
        if _vv is None:
            _vv = Voicevox()
        x = _vv(text, v)
        np.save(path, x)
    idx = np.where(np.abs(x) > 0.006)[0]
    x = x[max(0, idx[0] - 1500): idx[-1] + 3000].copy()
    f = 400
    x[:f] *= np.linspace(0, 1, f); x[-f * 3:] *= np.linspace(1, 0, f * 3)
    return x


# ---------------------------------------------------------------- 信号処理の道具
rng = np.random.default_rng(20261123)

def T(sec): return np.arange(int(sec * SR)) / SR

def lp(x, fc, order=2): b, a = signal.butter(order, fc / (SR / 2)); return signal.lfilter(b, a, x)
def hp(x, fc, order=2): b, a = signal.butter(order, fc / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def bp(x, lo, hi, order=2): b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band'); return signal.lfilter(b, a, x)

def norm(x, peak=1.0):
    m = np.max(np.abs(x)); return x / m * peak if m > 0 else x

def brown(n):
    x = np.cumsum(rng.standard_normal(n)); x = hp(x, 15, 1); return norm(x)

_irs = {}
def ir(rt60, damp=5000, pre=0.012, seed=0):
    """減衰ノイズで作るステレオ残響 IR"""
    key = (rt60, damp, pre, seed)
    if key not in _irs:
        r = np.random.default_rng(seed)
        n = int(rt60 * 1.3 * SR); t = np.arange(n) / SR
        env = 10 ** (-3 * t / rt60)
        chans = []
        for c in range(2):
            y = r.standard_normal(n) * env
            y = lp(y, damp, 1)
            y = np.concatenate([np.zeros(int(pre * SR)), y])
            chans.append(y / np.sqrt(np.sum(y ** 2)))
        _irs[key] = np.array(chans)
    return _irs[key]

def reverb(x, rt60, wet, damp=5000, pre=0.012, seed=0):
    """mono か (2,n) を受け取り、(2, n+tail) のステレオを返す"""
    x = np.atleast_2d(x)
    if x.shape[0] == 1: x = np.vstack([x, x])
    h = ir(rt60, damp, pre, seed)
    out = np.zeros((2, x.shape[1] + h.shape[1] - 1))
    for c in range(2):
        out[c, :x.shape[1]] += x[c] * (1 - wet)
        out[c] += signal.fftconvolve(x[c], h[c]) * wet * 3.0
    return out

def modes(spec, sec, phase_rng=True):
    """(周波数, 振幅, 減衰τ) の減衰正弦の和"""
    t = T(sec); x = np.zeros_like(t)
    for f, a, tau in spec:
        x += a * np.sin(2 * np.pi * f * t + (rng.uniform(0, 6.28) if phase_rng else 0)) * np.exp(-t / tau)
    return x * np.minimum(1, t / 0.0012)

def stereo(x, pan=0.0):
    """pan: -1(左)〜+1(右)、等パワー"""
    a = (pan + 1) * np.pi / 4
    return np.vstack([x * np.cos(a), x * np.sin(a)]) * np.sqrt(2)


# ---------------------------------------------------------------- 効果音
def knock_wood(gain=1.0, muffle=2200):
    """壁越しのノック(こもった木の音)"""
    x = modes([(92, 1.0, 0.055), (148, 0.8, 0.045), (231, 0.55, 0.03), (402, 0.3, 0.018), (760, 0.15, 0.01)], 0.4)
    click = bp(rng.standard_normal(len(x)), 500, 2500) * np.exp(-T(0.4) / 0.004)
    x = lp(x + 0.6 * click, muffle)
    return reverb(norm(x, gain), 0.5, 0.28, damp=3000, seed=1)

def knock_glass(gain=1.0):
    """窓ガラスを叩く音 + 窓枠のビビり"""
    x = modes([(1040, 0.7, 0.03), (1730, 0.5, 0.02), (2460, 0.35, 0.013), (3610, 0.2, 0.008), (155, 0.6, 0.03)], 0.35)
    rattle = bp(rng.standard_normal(len(x)), 1800, 4200) * np.exp(-T(0.35) / 0.03) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 47 * T(0.35))))
    click = hp(rng.standard_normal(len(x)), 2000) * np.exp(-T(0.35) / 0.002)
    x = x + 0.25 * rattle + 0.4 * click
    return reverb(norm(x, gain), 0.6, 0.3, damp=6000, seed=2)

def knock_door(gain=1.0):
    """鉄の玄関ドア(ゴン、という低い金属音)"""
    low = modes([(74, 1.0, 0.13), (118, 0.7, 0.09), (181, 0.5, 0.06)], 0.9)
    metal = modes([(312, 0.22, 0.34), (497, 0.18, 0.27), (741, 0.13, 0.2), (1063, 0.09, 0.14), (1489, 0.06, 0.1), (2210, 0.03, 0.06)], 0.9)
    click = bp(rng.standard_normal(len(low)), 300, 3000) * np.exp(-T(0.9) / 0.005)
    x = lp(low + metal + 0.5 * click, 4000)
    return reverb(norm(x, gain), 0.8, 0.35, damp=4000, seed=3)

def title_hit():
    """タイトルの重い打撃音(逆再生の吸い込み → 低いブーム)"""
    pre = 0.7
    swell = bp(rng.standard_normal(int(pre * SR)), 200, 3000) * np.linspace(0, 1, int(pre * SR)) ** 3
    swell = reverb(swell[::-1], 1.6, 0.9, seed=4)[:, ::-1][:, -int(pre * SR):]   # 逆残響
    t = T(3.0)
    f = 32 + 36 * np.exp(-t / 0.25)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    boom = np.tanh(boom * 3) * 0.8
    hit = lp(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.12) * 0.6
    body = reverb(boom + hit, 3.0, 0.45, damp=2500, seed=5)
    out = np.zeros((2, int(pre * SR) + body.shape[1]))
    out[:, :swell.shape[1]] += norm(swell, 0.35)
    out[:, int(pre * SR):] += norm(body, 1.0)
    return out, pre     # pre = 打撃までの先行時間

def dread_hit():
    """気付きの瞬間の不協和な低音(ブワーン)"""
    t = T(4.0)
    x = np.zeros_like(t)
    for f in (49.0, 51.9, 73.4, 77.8):
        x += signal.sawtooth(2 * np.pi * f * t + rng.uniform(0, 6))
    env = np.minimum(1, t / 0.04) * np.exp(-t / 1.3)
    cut = 180 + 900 * np.exp(-t / 0.4)
    # 時変ローパス(ブロック処理)
    y = np.zeros_like(x); blk = 2400; zi = None
    for i in range(0, len(x), blk):
        b, a = signal.butter(2, cut[i] / (SR / 2))
        if zi is None: zi = signal.lfilter_zi(b, a) * 0
        y[i:i + blk], zi = signal.lfilter(b, a, x[i:i + blk], zi=zi)
    y = np.tanh(y * env * 1.6)
    sub = np.sin(2 * np.pi * 36 * t) * np.exp(-t / 0.9) * np.minimum(1, t / 0.01)
    return reverb(norm(y, 0.7) + 0.6 * sub, 2.5, 0.35, damp=2000, seed=6)

def thunder():
    """稲光の破裂音 + 長い遠雷"""
    t = T(5.0)
    crack = hp(rng.standard_normal(len(t)), 900) * (np.exp(-t / 0.05) + 0.5 * np.exp(-np.maximum(t - 0.18, 0) / 0.04) * (t > 0.18))
    rumble = lp(brown(len(t)), 160, 2) * np.minimum(1, t / 0.25) * np.exp(-t / 1.4)
    rumble *= 0.6 + 0.4 * lp(np.abs(rng.standard_normal(len(t))), 6, 1) * 4
    L = norm(crack, 0.5) + norm(rumble, 0.9)
    R = norm(np.roll(crack, 180), 0.5) + norm(lp(brown(len(t)), 160, 2) * np.minimum(1, t / 0.25) * np.exp(-t / 1.4), 0.9)
    return reverb(np.vstack([L, R]), 2.0, 0.3, damp=3000, seed=7)

def scare():
    """ジャンプスケアの一撃: 衝撃 + 不協和音の刺突 + 金切り声(飽和させて密度を上げ、リミッタに潰されにくくする)"""
    t = T(3.2)
    impact = lp(rng.standard_normal(len(t)), 5000) * np.exp(-t / 0.07)
    sub = np.sin(2 * np.pi * np.cumsum(30 + 40 * np.exp(-t / 0.15)) / SR) * np.exp(-t / 0.9)
    stab = np.zeros_like(t)
    vib = 1 + 0.012 * np.sin(2 * np.pi * 7.3 * t)
    for f in (196, 207.7, 233.1, 277.2, 293.7, 415.3, 440, 554.4, 587.3, 830.6, 880):
        stab += signal.sawtooth(2 * np.pi * np.cumsum(f * vib * (1 + rng.uniform(-0.004, 0.004))) / SR)
    stab = lp(stab, 6000) * np.minimum(1, t / 0.004) * np.exp(-t / 0.8)
    f0 = 1250 + 400 * np.minimum(1, t / 0.5) + 1800 * lp(rng.standard_normal(len(t)), 30, 1)
    scr = signal.sawtooth(2 * np.pi * np.cumsum(f0) / SR)
    scr = bp(scr, 2200, 4200) * np.minimum(1, t / 0.01) * np.exp(-t / 0.6)
    dry = norm(impact, 0.7) + norm(sub, 0.9) + norm(stab, 1.0) + norm(scr, 0.5)
    dry = np.tanh(norm(dry) * 2.5)                       # 歪ませてクレストファクタを下げる
    wet = reverb(dry, 2.2, 0.35, damp=4500, seed=8)
    side = wet[0] - wet[1]; mid = (wet[0] + wet[1]) / 2
    wet = np.vstack([mid + 0.25 * side, mid - 0.25 * side])   # 左右の広がりを抑えて芯を残す
    return np.tanh(norm(wet) * 1.6)


def heartbeat_track(n, t0, t1, bpm0=58, bpm1=104):
    out = np.zeros(n); t = t0
    beat = lambda f, g: np.sin(2 * np.pi * f * T(0.25)) * (T(0.25) / 0.02) * np.exp(1 - T(0.25) / 0.02) * g
    lub, dub = lp(beat(52, 1.0), 200), lp(beat(63, 0.65), 200)
    while t < t1:
        p = (t - t0) / (t1 - t0)
        bpm = bpm0 + (bpm1 - bpm0) * p ** 1.5
        g = 0.35 + 0.65 * p
        for off, s in ((0, lub), (0.27 * 60 / bpm * 1.1, dub)):
            i = int((t + off) * SR)
            if i + len(s) < n: out[i:i + len(s)] += s * g
        t += 60 / bpm
    return out

def riser(sec):
    """暗転直前まで上がり続ける緊張音(不協和クラスター + ノイズ)"""
    t = T(sec); p = t / sec
    bend = 2 ** ((5 / 12) * np.clip((p - 0.35) / 0.65, 0, 1) ** 2)
    x = np.zeros_like(t)
    for f in (110, 116.5, 123.5, 155.6, 164.8, 220, 233.1, 311.1):
        x += signal.sawtooth(2 * np.pi * np.cumsum(f * bend * (1 + rng.uniform(-0.003, 0.003))) / SR)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(2 + 12 * p ** 2) / SR)
    x = lp(x, 2500) * trem
    noise = bp(rng.standard_normal(len(t)), 800, 6000) * p ** 2
    env = 10 ** ((-38 + 34 * p ** 1.6) / 20)
    y = (norm(x) * 0.8 + norm(noise) * 0.4) * env
    y[-int(0.006 * SR):] *= np.linspace(1, 0, int(0.006 * SR))
    return y


# ---------------------------------------------------------------- 台本を時刻に展開
def chant(text, memory=False):
    """3人で声をそろえて唱える(全員四国めたん)。memory=True は回想用に遠く・こもらせる"""
    xs = [speak(k, text) for k in ('C1', 'C2', 'C3')]
    n = max(len(x) for x in xs) + int(0.08 * SR)
    out = np.zeros((2, n))
    for x, pan, dly, g in zip(xs, (-0.55, 0.55, 0.0), (0.0, 0.028, 0.055), (1.0, 0.85, 0.8)):
        i = int(dly * SR); out[:, i:i + len(x)] += stereo(x, pan)[:, :n - i] * g
    if memory:
        out = np.vstack([bp(out[0], 250, 3200), bp(out[1], 250, 3200)])
        out *= 1 + 0.25 * np.sin(2 * np.pi * 5.5 * np.arange(n) / SR)      # 古いテープのような揺れ
        return reverb(out, 2.4, 0.55, damp=3000, seed=11)[:, :n + int(0.3 * SR)]
    return reverb(out, 0.9, 0.22, damp=5000, seed=12)[:, :n + int(0.2 * SR)]

def coin_move(sec):
    """紙の上を十円玉がすべる音(速さに合わせて強弱)+ 止まるときの小さな音"""
    t = T(sec); p = t / sec
    speed = np.sin(np.pi * p) ** 0.7
    rub = bp(rng.standard_normal(len(t)), 1800, 7000) * 0.6 + bp(rng.standard_normal(len(t)), 300, 900) * 0.5
    grain = 1 + 0.6 * lp(rng.standard_normal(len(t)), 40, 1) * 8
    x = rub * speed * grain
    tick = modes([(3100, 0.3, 0.004), (5200, 0.2, 0.003)], 0.05)
    out = np.concatenate([x, np.zeros(len(tick))]); out[len(x):] += tick
    return out

def chalk_line(sec):
    """チョークで1行書く音(ストロークごとに途切れるこすれ音)"""
    t = T(sec)
    strokes = (np.sin(2 * np.pi * np.cumsum(9 + 5 * lp(rng.standard_normal(len(t)), 3, 1) * 30) / SR) > -0.2).astype(float)
    strokes = lp(strokes, 60, 1)
    x = bp(rng.standard_normal(len(t)), 1500, 6500) * strokes * (1 + 0.5 * lp(rng.standard_normal(len(t)), 80, 1) * 6)
    return x * np.minimum(1, t / 0.02) * np.minimum(1, (sec - t) / 0.03)

def chalk_snap():
    x = hp(rng.standard_normal(int(0.03 * SR)), 1500) * np.exp(-T(0.03) / 0.004)
    out = np.zeros(int(0.5 * SR)); out[:len(x)] += x
    for d, g in ((0.16, 0.25), (0.27, 0.12)):      # 折れた欠片が床で跳ねる
        y = modes([(2400, g, 0.006), (4100, g * 0.6, 0.004)], 0.04); i = int(d * SR); out[i:i + len(y)] += y
    return reverb(out, 0.9, 0.3, seed=13)

def chime():
    """壊れかけの学校のチャイム(ウェストミンスターの鐘の旋律・パブリックドメイン)。テープが伸びたように揺れて下がっていく"""
    notes = [(329.6, 0.0), (261.6, 0.95), (293.7, 1.9), (196.0, 2.85), (196.0, 4.3), (293.7, 5.25), (329.6, 6.2), (261.6, 7.15)]
    total = 10.5; t = T(total)
    warp = (1 + 0.014 * np.sin(2 * np.pi * 0.6 * t) + 0.006 * np.sin(2 * np.pi * 2.3 * t)) * (1 - 0.06 * (t / total) ** 1.5)
    out = np.zeros(len(t))
    partials = [(0.5, 0.35, 2.5), (1.0, 1.0, 1.8), (1.183, 0.5, 1.2), (1.506, 0.35, 0.9), (2.0, 0.3, 0.8), (2.514, 0.18, 0.5), (3.011, 0.1, 0.35)]
    for f0, t0 in notes:
        i = int(t0 * SR); tt = t[: len(t) - i]
        ph = 2 * np.pi * np.cumsum(f0 * warp[i:]) / SR
        y = sum(a * np.sin(r * ph) * np.exp(-tt / d) for r, a, d in partials)
        out[i:] += y * np.minimum(1, tt / 0.004)
    out = lp(out, 3500)
    return reverb(out, 2.8, 0.5, damp=3000, seed=14)

def crow():
    """遠くのカラス(夕方の気配)"""
    out = np.zeros(int(2.4 * SR))
    for t0, f in ((0.0, 620), (0.55, 590), (1.5, 640)):
        t = T(0.34); p = t / 0.34
        f0 = f * (1.05 - 0.2 * p)
        x = signal.sawtooth(2 * np.pi * np.cumsum(f0) / SR) + 0.6 * rng.standard_normal(len(t))
        x = bp(x, 900, 2600) * np.sin(np.pi * p) ** 0.6
        i = int(t0 * SR); out[i:i + len(x)] += x
    return reverb(lp(out, 2800), 1.6, 0.45, damp=2500, seed=15)

def knock_slide():
    """教室の引き戸(木の枠 + はめ込みガラスのびびり)"""
    x = knock_wood(muffle=4500)
    g = knock_glass()
    n = max(x.shape[1], g.shape[1]); out = np.zeros((2, n))
    out[:, :x.shape[1]] += x; out[:, :g.shape[1]] += 0.45 * g
    return out


def build_timeline():
    t = 0.0; scenes = []; lines = []; sfx = []; marks = {}; voice_clips = []
    for ev in TIMELINE:
        k = ev[0]
        if k == 'scene':
            if scenes: scenes[-1]['end'] = round(t, 4)
            scenes.append({'name': ev[1], 'start': round(t, 4)})
        elif k == 'gap':
            t += ev[1]
        elif k == 'mark':
            marks[ev[1]] = round(t, 4)
        elif k == 'say':
            key, text = ev[1], ev[2]
            cap = ev[3] if len(ev) > 3 else text
            if key in ('C', 'CF'):
                x = chant(text, key == 'CF')
            else:
                x = speak(key, text)
            if key == 'G':
                x = ghostify(x)
            voice_clips.append((t, key, x))
            dur = x.shape[-1] / SR - (GHOST_PRE if key == 'G' else 0)
            lines.append({'start': round(t, 4), 'end': round(t + dur, 4), 'text': cap, 'voice': key})
            t += dur
        elif k == 'sfx':
            args = ev[3] if len(ev) > 3 else {}
            e = {'name': ev[1], 't': round(t, 4)}
            if 'hits' in args: e['hits'] = [round(t + h, 4) for h in args['hits']]
            if 'path' in args:
                e['path'] = [[c, round(t + a, 4), round(t + b, 4)] for c, a, b in args['path']]
                e['reset'] = bool(args.get('reset'))
            if 'lines' in args:
                e['writes'] = [[round(t + i * args['step'], 4), round(t + i * args['step'] + args['len'], 4)] for i in range(args['lines'])]
            sfx.append(e)
            t += ev[2]
    scenes[-1]['end'] = round(t, 4)
    return t, scenes, lines, sfx, marks, voice_clips

GHOST_PRE = 0.6   # 幽霊の声の前に付く逆残響の吸い込み(秒)

def ghostify(x):
    """ささやき声を「耳元の何か」に: 低くした声 + 元の声 + 逆残響の吸い込み、右耳に寄せる"""
    low = signal.resample_poly(x, 6, 5)          # 1.2 倍に伸ばす = 約3半音低く・遅く
    n = len(low)
    hi = np.zeros(n); hi[:len(x)] = x
    body = 0.9 * low + 0.28 * hp(hi, 400)
    pre = int(GHOST_PRE * SR)
    rev = reverb(np.concatenate([body[::-1], np.zeros(pre)]), 1.8, 1.0, seed=9)[:, :n + pre][:, ::-1]
    out = np.zeros((2, n + pre))
    out[:, pre:] += stereo(body, 0.55)
    d = int(0.0006 * SR)       # 両耳時間差で右耳のすぐ後ろに定位させる
    out[0, pre + d:] = out[0, pre:-d].copy() * 0.8
    out += norm(rev, 0.25)
    return out


def main():
    total, scenes, lines, sfx, marks, voice_clips = build_timeline()
    N = int((total + 0.05) * SR) + 1
    voice = np.zeros((2, N)); fx = np.zeros((2, N)); bed = np.zeros((2, N))

    def add(buf, t, x, gain=1.0):
        x = np.atleast_2d(x)
        if x.shape[0] == 1: x = np.vstack([x, x])
        i = int(round(t * SR)); j = min(N, i + x.shape[1])
        if i < 0: x = x[:, -i:]; i = 0
        buf[:, i:j] += x[:, :j - i] * gain

    def stmax(x):
        """短期音量: 400ms RMS の最大値 (dBFS)"""
        a = np.atleast_2d(x).mean(axis=0); w = int(0.4 * SR)
        if len(a) < w: a = np.pad(a, (0, w - len(a)))
        r = np.sqrt(np.convolve(a ** 2, np.ones(w) / w, mode='valid'))
        return 20 * np.log10(r.max() + 1e-12)

    def rmsdb(x):
        return 20 * np.log10(np.sqrt(np.mean(np.atleast_2d(x).mean(axis=0) ** 2)) + 1e-12)

    # --- ナレーション: 1本ずつ短期音量をそろえ、子音のとがったピークだけ削る
    ghost = np.zeros((2, N))
    for t, key, x in voice_clips:
        rel = VOICE_REL[key]
        y = x if key in ('G', 'C', 'CF') else reverb(x, 0.45, 0.09, damp=6000, seed=10)
        add(ghost if key == 'G' else voice, t - (GHOST_PRE if key == 'G' else 0), y, 10 ** ((VREF + rel - stmax(y)) / 20))
    voice = limiter(voice, ceiling=10 ** ((VREF + 8) / 20)) + ghost   # 囁き声はピークがとがるのでリミッタを通さない
    voice_mono = voice.mean(axis=0)

    # --- 効果音: ナレーションの短期音量 VREF に対する相対 dB (SFX_REL) で置く
    sc = {s['name']: s for s in scenes}
    def place(t, x, rel):
        add(fx, t, x, 10 ** ((VREF + rel - stmax(x)) / 20))
    for e in sfx:
        nm, t = e['name'], e['t']
        if nm in ('knock_wood', 'knock_soft', 'knock_glass', 'knock_door', 'knock_slide'):
            for i, h in enumerate(e['hits']):
                x = {'knock_wood': lambda: knock_wood(), 'knock_soft': lambda: knock_wood(muffle=1200),
                     'knock_glass': knock_glass, 'knock_door': knock_door, 'knock_slide': knock_slide}[nm]()
                place(h, x, SFX_REL[nm] + (0.8 * i if nm != 'knock_soft' else 0))   # 3回目に向けて少しずつ強く
        elif nm == 'coin':
            for c, a, b in e['path']: place(a, coin_move(b - a), SFX_REL[nm])
        elif nm == 'chalk':
            for a, b in e['writes']: place(a, chalk_line(b - a), SFX_REL[nm])
        elif nm == 'title_hit':
            x, pre = title_hit(); place(t + 0.05 - pre, x, SFX_REL[nm])
        else:
            place(t, {'dread_hit': dread_hit, 'thunder': thunder, 'scare': scare, 'chalk_snap': chalk_snap,
                      'chime': chime, 'crow': crow}[nm](), SFX_REL[nm])

    # --- 環境音(シーンごとの量をなめらかに切り替える)
    tt = np.arange(N) / SR
    drone = np.zeros((2, N))
    for c in range(2):
        d = 0.0
        for f, a in ((36.7, 0.8), (55.0, 0.6), (55.0 + 0.37 + 0.11 * c, 0.5), (73.4, 0.25), (82.4 * (1 + 0.002 * c), 0.15)):
            d += a * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6))
        d *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * tt + c)
        drone[c] = d + 0.6 * lp(brown(N), 120)
    drone = norm(drone, 1.0)
    high = np.zeros((2, N))
    for c in range(2):
        high[c] = (np.sin(2 * np.pi * (1174.7 + c * 0.6) * tt) + 0.8 * np.sin(2 * np.pi * 1244.5 * tt + c)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * tt + 2 * c))
    high = norm(high, 1.0)
    roomtone = norm(np.vstack([lp(brown(N), 400) + 0.05 * lp(rng.standard_normal(N), 3000) for _ in range(2)]), 1.0)
    wind = np.zeros((2, N))
    for c in range(2):
        w = rng.standard_normal(N)
        cf = 500 + 250 * np.sin(2 * np.pi * 0.13 * tt + c * 1.7) + 120 * np.sin(2 * np.pi * 0.31 * tt)
        y = np.zeros(N); blk = 4800; zi = np.zeros(4)
        for i in range(0, N, blk):
            b, a = signal.butter(2, [max(80, cf[i] * 0.7) / (SR / 2), cf[i] * 1.4 / (SR / 2)], 'band')
            y[i:i + blk], zi = signal.lfilter(b, a, w[i:i + blk], zi=zi)
        wind[c] = y * (0.6 + 0.4 * lp(np.abs(rng.standard_normal(N)), 0.5, 1) * 3)
    wind = norm(wind, 1.0)
    # 蛍光灯のうなり(廊下)
    hum = sum(np.sin(2 * np.pi * 100 * k * tt) / k for k in range(1, 14))
    hum = lp(hum, 1800) + 0.3 * np.sin(2 * np.pi * 50 * tt)
    hum = norm(hum, 1.0)
    tinnitus = norm(np.sin(2 * np.pi * 7040 * tt) + 0.5 * np.sin(2 * np.pi * 5110 * tt), 1.0)

    light = np.ones(N); clicks = np.zeros(N)

    BED = {   # drone, high, roomtone, wind, hum, tinnitus
        'hall': (0.5, 0.25, 0.8, 0.12, 0, 0), 'title': (1.0, 0.0, 0.5, 0, 0, 0), 'board': (0.45, 0.2, 0.8, 0, 0, 0),
        'sheet': (0.4, 0.2, 0.7, 0.1, 0, 0), 'classdoor': (0.8, 0.35, 0.8, 0.1, 0, 0), 'sheet2': (0.85, 0.35, 0.6, 0, 0, 0),
        'window': (0.6, 0.3, 0.7, 0.4, 0, 0), 'clock': (0.25, 0.0, 0.6, 0, 0, 1.0),
        'dark': (0.5, 0.25, 0.7, 0, 0, 0.4), 'flash': (0.6, 0.4, 0.4, 0, 0, 0.6),
        'black': (0, 0, 0.12, 0, 0, 0), 'scare': (0, 0, 0, 0, 0, 0), 'outro': (0.4, 0.1, 0.4, 0, 0, 0),
    }
    G = np.zeros((6, N))
    for s in scenes:
        i, j = int(s['start'] * SR), int(s['end'] * SR)
        G[:, i:j] = np.array(BED[s['name']])[:, None]
    G[:, int(scenes[-1]['end'] * SR):] = np.array(BED['outro'])[:, None]
    k = int(0.35 * SR); ker = np.ones(k) / k
    blk = 480
    Gs = np.array([np.repeat(np.convolve(g[::blk], np.ones(k // blk) / (k // blk), mode='same'), blk)[:N] for g in G])
    # 暗転〜スケアは環境音を即座に切る
    hard = np.ones(N)
    hard[int(sc['black']['start'] * SR):int(sc['scare']['end'] * SR)] = 0
    Gs[[0, 1, 3, 4, 5]] *= hard
    Gs[2] = np.where(hard == 0, G[2], Gs[2])

    # ナレーション中は環境音を少し下げる(ダッキング)
    hop = SR // 50
    env = np.sqrt(np.convolve(voice_mono ** 2, np.ones(hop) / hop, mode='same'))
    duck = 1 - 0.4 * np.clip(env / 10 ** ((VREF - 8) / 20), 0, 1)
    duck = np.convolve(duck[::blk], np.ones(30) / 30, mode='same').repeat(blk)[:N]

    def lvl(x, rel):   # 連続音を「ゲイン 1 のとき VREF + rel dB (RMS)」に合わせる
        return x * 10 ** ((VREF + rel - rmsdb(x)) / 20)
    bed = (lvl(drone, BED_REL['drone']) * Gs[0] + lvl(high, BED_REL['high']) * Gs[1]
           + lvl(roomtone, BED_REL['room']) * Gs[2] + lvl(wind, BED_REL['wind']) * Gs[3]
           + lvl(hum, BED_REL['hum']) * Gs[4] * light + clicks * 10 ** ((VREF + 4) / 20) * Gs[4]
           + lvl(tinnitus, BED_REL['tinnitus']) * Gs[5]) * duck

    # 心音(時計のシーン〜暗転まで)、緊張音(暗いシーン〜暗転)
    hb = heartbeat_track(N, sc['clock']['start'] + 0.3, sc['black']['start'])
    add(fx, 0, stereo(hb), 10 ** ((VREF + SFX_REL['heartbeat'] - stmax(hb)) / 20))
    d = {'start': sc['dark']['start'], 'end': sc['black']['start']}; rs = riser(d['end'] - d['start'])
    add(fx, d['start'], stereo(rs), 10 ** ((VREF + SFX_REL['riser'] - stmax(rs[-SR:])) / 20))

    mix = voice + fx + bed

    def lufs(x):
        p = os.path.join(OUT, '_tmp.wav'); write_wav(p, x)
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        os.remove(p)
        I = float(r.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
        TP = float(r.split('True peak:')[1].split('Peak:')[1].split('dBFS')[0])
        return I, TP
    # 声のラウドネスを基準に全体のゲインを決め、はみ出すピーク(主にスケア)だけリミッタで抑える
    vI, _ = lufs(voice)
    g = 10 ** ((VOICE_LUFS - vI) / 20)
    mix = limiter(mix * g, ceiling=10 ** (-2.6 / 20)); voice = voice * g
    I, TP = lufs(mix)
    print(f'  voice {VOICE_LUFS:.1f} LUFS → mix {I:.1f} LUFS, true peak {TP:.1f} dBTP')

    # 各イベントの短期ラウドネス(400ms RMS の最大)を表示して、バランスを確認する
    def st(t0, t1):
        a = mix[:, int(t0 * SR):int(t1 * SR)].mean(axis=0)
        w = int(0.4 * SR); r = np.sqrt(np.convolve(a ** 2, np.ones(w) / w, mode='valid'))
        return 20 * np.log10(r.max() + 1e-9), 20 * np.log10(np.abs(a).max() + 1e-9)
    for e in sfx:
        print('  sfx %-12s %6.2fs  st-max %6.1f dB  peak %6.1f' % ((e['name'], e['t']) + st(e['t'], e['t'] + 1.5)))
    print('  riser end          st-max %6.1f dB  peak %6.1f' % st(sc['black']['start'] - 1.0, sc['black']['start']))
    for l in (lines[0], lines[2], lines[9]):
        print('  voice %-12s st-max %6.1f dB  peak %6.1f' % ((l['text'][:6],) + st(l['start'], l['end'])))
    print('  clock(heartbeat)   st-max %6.1f dB  peak %6.1f' % st(sc['clock']['start'], sc['clock']['end']))
    print('  black(ghost)       st-max %6.1f dB  peak %6.1f' % st(sc['black']['start'], sc['black']['end']))
    write_wav(os.path.join(OUT, 'mix.wav'), mix)
    write_wav(os.path.join(OUT, 'narration.wav'), voice)

    tl = {'fps': FPS, 'duration': round(total, 4), 'scenes': scenes, 'lines': lines, 'sfx': sfx, 'marks': marks}
    with open(os.path.join(OUT, 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'subtitles_ja.srt'), 'w', encoding='utf-8') as f:
        for i, l in enumerate(lines, 1):
            f.write(f"{i}\n{srt_ts(l['start'])} --> {srt_ts(l['end'] + 0.25)}\n{l['text']}\n\n")
    print(f'duration {total:.2f}s')
    for s in scenes: print(f"  {s['start']:6.2f}–{s['end']:6.2f}  {s['name']}")
    for l in lines: print(f"  {l['start']:6.2f}–{l['end']:6.2f}  [{l['voice']}] {l['text']}")


def limiter(x, ceiling, look=0.004, release=0.12):
    peak = np.max(np.abs(x), axis=0)
    g = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    w = int(look * SR)
    g = minimum_filter1d(g, 2 * w + 1)
    # 1ms ブロックでリリースを付ける
    b = SR // 1000
    n = len(g) // b * b
    gb = g[:n].reshape(-1, b).min(axis=1)
    out = np.empty_like(gb); cur = 1.0; coef = 1 / (release * 1000)
    for i, v in enumerate(gb):
        cur = v if v < cur else cur + (1 - cur) * coef
        cur = min(cur, v) if v < cur else cur
        out[i] = cur
    gs = np.concatenate([np.repeat(out, b), np.full(len(g) - n, out[-1])])
    gs = np.convolve(gs, np.ones(w) / w, mode='same')
    gs = np.minimum(gs, g)
    return x * gs

def write_wav(path, x):
    x = np.atleast_2d(x)
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16).T.copy()
    with wave.open(path, 'wb') as w:
        w.setnchannels(y.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(y.tobytes())

def srt_ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}'


if __name__ == '__main__':
    main()
