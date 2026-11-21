#!/usr/bin/env python3
"""【意味がわかると怖い】祖母の数え歌 — ショート動画生成スクリプト (v3).

縦型 1080x1920 / 30fps / 60秒未満。ナレーションは VOICEVOX:四国めたん、
映像・音楽・効果音もすべてプログラムで生成する。

使い方:  python3 make_video.py [出力パス]
必要:    ffmpeg, numpy, Pillow, IPAフォント, voicevox_core 0.17（+ onnxruntime・open_jtalk辞書・0.vvm・s0.vvm）

構成
  0. つかみ   祖母が毎晩歌ってくれた数え歌。大人になって、やっと意味がわかった。
  1. 数え歌   四国めたんが歌う。夕暮れのあぜ道を歩く二人の子ども（歌詞どおりに一人になって帰ってくる）
  2. 写真     祖母には妹がいた。七つのとき、井戸の近くでいなくなった。村では七つまでは神さまの子。
  3. 紙       祖母の部屋で見つけた歌詞。数字の下の一文字だけ赤丸 → 「わたしがうめた」
  4. オチ     昨日、祖母が妹にこの歌を教えていた。妹は、来週、七つになる。
              祖母はいつも最後に言った。「お姉ちゃんなんだから、ちゃんと覚えるんだよ」
              （歌の「わたし」は歌う姉。次に埋めるのは語り手自身）
"""
import hashlib
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
SR = 44100
HERE = Path(__file__).resolve().parent
BUILD = HERE / ".build"
BUILD.mkdir(exist_ok=True)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else HERE / "kazoeuta_horror.mp4"

MINCHO = "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf"
GOTHIC = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
try:
    ImageFont.truetype(MINCHO, 10)
except OSError:
    MINCHO = GOTHIC
# VOICEVOX（四国めたん）。場所は環境変数で変更可
VV_DIR = Path(__import__("os").environ.get("VOICEVOX_DIR", "/root/voicevox"))
VV_STYLE = 2          # 四国めたん（ノーマル）
CREDIT = "VOICEVOX:四国めたん"

rng = np.random.default_rng(11)

# 数字の次の一文字を縦に読むと「わたしがうめた」
LYRICS = [
    "ひとつ　わらって　てをつなぎ",
    "ふたつ　たんぼの　あぜみちを",
    "みっつ　しずかに　ふたりきり",
    "よっつ　がけした　いどのそば",
    "いつつ　うしろで　ないてても",
    "むっつ　めかくし　ふたをして",
    "ななつ　たったひとりで　かえりみち",
]
HIDDEN = "".join(l.split("　")[1][0] for l in LYRICS)
assert HIDDEN == "わたしがうめた", HIDDEN
CIRCLE = 0.6          # 赤丸の間隔

# ---- 歌（四国めたんが歌う）。都節音階 D Eb G A Bb D'
D4, Eb4, G4, A4, Bb4, D5 = 62, 63, 67, 69, 70, 74
MELODY = [   # 各行：数え言葉 / 二語目 / 三語目 の音高（1モーラ1音）
    [[A4, A4, G4], [A4, Bb4, A4, G4], [A4, G4, Eb4, D4, D4]],
    [[A4, A4, G4], [A4, Bb4, D5, Bb4], [A4, G4, A4, G4, G4]],
    [[Bb4, Bb4, A4], [G4, A4, G4, Eb4], [G4, Eb4, D4, Eb4, D4]],
    [[G4, G4, A4], [Bb4, A4, G4, A4], [A4, G4, Eb4, Eb4, D4]],
    [[A4, A4, G4], [A4, Bb4, A4, G4], [A4, G4, Eb4, D4, D4]],
    [[A4, Bb4, D5], [D5, Bb4, A4, G4], [A4, G4, Eb4, Eb4, D4]],
    [[D4, D4, Eb4], [G4, G4, G4, A4, G4, Eb4, Eb4], [D4, Eb4, D4, Eb4, D4]],
]
FPS_SING = 93.75
EIGHTH_F = 22                       # 8分音符 = 22フレーム（約0.23秒）
EIGHTH = EIGHTH_F / FPS_SING


def kata(text):
    k = "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in text)
    return k.replace("ヲ", "オ")      # 歌唱APIは「ヲ」を受け付けないので同じ音の「オ」に


def build_score():
    lines = []
    for li, (lyric, mel) in enumerate(zip(LYRICS, MELODY)):
        words = lyric.split("　")
        last = li == len(LYRICS) - 1
        notes = []
        for wi, (w, keys) in enumerate(zip(words, mel)):
            assert len(w) == len(keys), (w, keys)
            for mi, (ch, k) in enumerate(zip(w, keys)):
                e = 1
                if wi == 0 and mi == len(w) - 1:
                    e = 2
                if wi == 2 and mi == len(w) - 1:
                    e = 5 if last else 3
                notes.append((kata(ch), k, e))
        rest = 3 if last else 1
        lines.append((notes, sum(n[2] for n in notes) + rest))
    return lines


SCORE = build_score()
LINE_DUR = [tot * EIGHTH for _, tot in SCORE]
LINE_START = list(np.cumsum([0.0] + LINE_DUR[:-1]))
SONG_LEN = sum(LINE_DUR)


def song_pos(st):
    """歌の開始からの経過秒 → (行番号, 行内の進み 0..1)."""
    if st < 0:
        return -1, 0.0
    for i in range(len(LINE_DUR) - 1, -1, -1):
        if st >= LINE_START[i]:
            return i, min(1.0, (st - LINE_START[i]) / LINE_DUR[i])
    return 0, 0.0


# ================================================================ 音声ユーティリティ
def fftconv(x, k):
    n = len(x) + len(k) - 1
    nf = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(k, nf), nf)[:n]


def reverb_ir(sec, decay, seed=1):
    r = np.random.default_rng(seed)
    t = np.arange(int(sec * SR)) / SR
    ir = np.convolve(r.standard_normal(len(t)) * np.exp(-t * decay), np.ones(6) / 6, mode="same")
    ir[0] = 0
    return ir / np.sqrt(np.sum(ir ** 2))


def resample(x, ratio):
    n = int(len(x) * ratio)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def smooth(x, win):
    return np.convolve(x, np.ones(win) / win, mode="same")


IR_ROOM = reverb_ir(0.7, 7, 1)
IR_HALL = reverb_ir(2.2, 2.6, 2)


_SYN = None


def _synth():
    global _SYN
    if _SYN is None:
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        so = sorted(VV_DIR.glob("voicevox_onnxruntime-*/lib/libvoicevox_onnxruntime.so*"))[0]
        _SYN = Synthesizer(Onnxruntime.load_once(filename=str(so)), OpenJtalk(str(VV_DIR / "open_jtalk_dic_utf_8-1.11")))
        with VoiceModelFile.open(str(VV_DIR / "vv/models/0.vvm")) as m:
            _SYN.load_voice_model(m)
    return _SYN


def tts(text, speed=1.0, pitch=0.0, intonation=1.0):
    """四国めたんで読み上げ（キャッシュあり）."""
    key = hashlib.md5(f"vv{VV_STYLE}|{text}|{speed}|{pitch}|{intonation}".encode()).hexdigest()[:12]
    path = BUILD / f"vv_{key}.wav"
    if not path.exists():
        syn = _synth()
        q = syn.create_audio_query(text, VV_STYLE)
        q.speed_scale, q.pitch_scale, q.intonation_scale = speed, pitch, intonation
        q.pre_phoneme_length, q.post_phoneme_length = 0.05, 0.1
        path.write_bytes(syn.synthesis(q, VV_STYLE))
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    x = resample(x, SR / sr)
    idx = np.where(np.abs(x) > 0.01)[0]
    x = x[max(0, idx[0] - 400): idx[-1] + 2000]
    return x / (np.max(np.abs(x)) + 1e-9)


def grandma(text):
    """記憶の中の祖母の声（低く・ゆっくり・遠い残響）."""
    x = tts(text, speed=0.8, pitch=-0.13, intonation=0.7)
    wet = fftconv(x, IR_HALL)[: len(x) + int(1.2 * SR)]
    y = np.pad(x, (0, len(wet) - len(x))) + 0.35 * wet
    y = smooth(y, 3)
    return y / np.max(np.abs(y)) * 0.75


def narrator(text):
    """静かに語る四国めたん（ほんの少し部屋の残響）."""
    x = tts(text, speed=0.9, pitch=-0.03, intonation=0.85)
    wet = fftconv(x, IR_ROOM)[: len(x) + int(0.5 * SR)]
    y = np.pad(x, (0, len(wet) - len(x))) + 0.10 * wet
    return y / np.max(np.abs(y)) * 0.8


SING_TEACHER = 6000   # 歌唱用の音高モデル
SING_STYLE = 3002     # 四国めたん（歌唱・ノーマル）
SING_WHISPER = 3037   # 四国めたん（歌唱・ヒソヒソ）
_SING = None


def _singer():
    global _SING
    if _SING is None:
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        so = sorted(VV_DIR.glob("voicevox_onnxruntime-*/lib/libvoicevox_onnxruntime.so*"))[0]
        _SING = Synthesizer(Onnxruntime.load_once(filename=str(so)), OpenJtalk(str(VV_DIR / "open_jtalk_dic_utf_8-1.11")))
        with VoiceModelFile.open(str(VV_DIR / "vv/models/s0.vvm")) as m:
            _SING.load_voice_model(m)
    return _SING


LEAD_F = 10   # 歌い出し前の休符（フレーム）


def sing(notes, style=SING_STYLE):
    """notes: [(カタカナ1モーラ, MIDI, 8分音符の数)] → 歌声（先頭の休符ぶんを除いて返す）."""
    from voicevox_core import Note, Score
    key = hashlib.md5(f"sing{style}|{EIGHTH_F}|{notes}".encode()).hexdigest()[:12]
    path = BUILD / f"sing_{key}.wav"
    if not path.exists():
        syn = _singer()
        sc = [Note(LEAD_F, "")] + [Note(e * EIGHTH_F, ch, k) for ch, k, e in notes] + [Note(30, "")]
        q = syn.create_sing_frame_audio_query(Score(sc), SING_TEACHER)
        path.write_bytes(syn.frame_synthesis(q, style))
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    x = resample(x, SR / sr)[int(LEAD_F / FPS_SING * SR):]
    return x / (np.max(np.abs(x)) + 1e-9)


def midi_hz(k):
    return 440.0 * 2 ** ((k - 69) / 12)


def pluck(freq, dur, amp=0.5, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 9):
        f = freq * k * (1 + 0.0007 * k * k)
        if f > SR / 2:
            break
        sig += (1.0 / k ** 1.25) * np.exp(-(2.2 + k * 1.3 / bright) * t) * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    return amp * sig * np.minimum(1, t / 0.004)


# ================================================================ タイムライン
class TL:
    def __init__(self):
        self.t = 0.0
        self.voice = []
        self.subs = []
        self.mark = {}

    def say(self, text, sub=None, gap=0.35, voice=None):
        sig = (voice or narrator)(text)
        loud = np.where(np.abs(sig) > 0.08)[0]
        dur = loud[-1] / SR
        self.voice.append((self.t, sig))
        self.subs.append((self.t, self.t + dur + 0.25, sub or text))
        self.t += dur + gap

    def wait(self, s):
        self.t += s


def build_timeline():
    tl = TL()
    tl.wait(0.2)
    tl.mark["hook"] = tl.t
    tl.say("祖母が毎晩、歌ってくれた、数え歌がある。", "祖母が毎晩\n歌ってくれた数え歌がある。")
    tl.say("大人になって、やっと、その意味がわかった。", "大人になって\nやっと、その意味がわかった。", gap=1.0)
    tl.mark["song"] = tl.t
    tl.t += SONG_LEN + 1.0
    tl.mark["photo"] = tl.t
    tl.say("祖母には、妹がいたらしい。", gap=0.7)
    tl.say("七つのとき、裏山の井戸の近くで、いなくなったそうだ。", "七つのとき\n裏山の井戸の近くで\nいなくなったそうだ。", gap=0.9)
    tl.say("村では、七つまでは、神さまの子だと、言われていた。", "村では\n七つまでは神さまの子だと\n言われていた。", gap=1.2)
    tl.mark["paper"] = tl.t
    tl.say("先日、祖母の部屋で、この歌詞を書いた、古い紙を見つけた。", "先日、祖母の部屋で\nこの歌詞を書いた古い紙を見つけた。", gap=0.6)
    tl.say("数字の下の一文字だけが、赤い丸で、囲んであった。", "数字の下の一文字だけが\n赤い丸で囲んであった。", gap=0.8)
    tl.mark["circles"] = tl.t
    tl.t += CIRCLE * len(LYRICS) + 0.8
    tl.mark["reveal"] = tl.t
    tl.t += 4.0
    tl.mark["end"] = tl.t
    tl.wait(0.4)
    tl.mark["end_hum"] = tl.t
    tl.say("昨日、祖母が、妹に、この歌を教えていた。", "昨日、祖母が妹に\nこの歌を教えていた。", gap=1.4)
    tl.mark["last"] = tl.t
    tl.say("妹は、来週、七つになる。", gap=1.6)
    tl.say("祖母は、いつも最後に、こう言った。", "祖母は、いつも最後に\nこう言った。", gap=0.9)
    tl.mark["turn"] = tl.t
    tl.say("お姉ちゃんなんだから、ちゃんと、覚えるんだよ。", "「お姉ちゃんなんだから\nちゃんと覚えるんだよ」", gap=0.2, voice=grandma)
    tl.t += 2.2
    tl.mark["dark"] = tl.t
    tl.t += 2.5
    tl.mark["dur"] = tl.t
    return tl


TLN = build_timeline()
M = TLN.mark
DUR = M["dur"]


# ================================================================ 音声ミックス
def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


BASE = 293.66
RAT = {0: 1.0, 1: 16 / 15, 2: 4 / 3, 3: 3 / 2, 4: 8 / 5, 5: 2.0}


def make_audio():
    n = int(DUR * SR) + SR
    mus = np.zeros(n)
    voc = np.zeros(n)
    t = np.arange(n) / SR

    # 環境音：ヒグラシ風の虫（歌の間）＋部屋の空気＋テープヒス
    cic_env = np.clip((t - M["song"] + 0.5) / 1.0, 0, 1) * np.clip((M["photo"] - t) / 1.0, 0, 1)
    cic = np.sin(2 * np.pi * 4200 * t + 3 * np.sin(2 * np.pi * 30 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * t)) ** 4
    mus += cic * cic_env * 0.02
    mus += smooth(rng.standard_normal(n), 120) * 0.25 * np.clip(t / 1.0, 0, 1)
    mus += smooth(rng.standard_normal(n), 2) * 0.006

    # 数え歌：四国めたんの歌＋琴（1オクターブ下でなぞる）
    for li, (notes, _) in enumerate(SCORE):
        st0 = M["song"] + LINE_START[li]
        v = sing(notes)
        v = v + 0.18 * fftconv(v, IR_HALL)[: len(v)]
        add(mus, st0, v, 0.55)
        tt0 = st0
        for ch, k, e in notes:
            add(mus, tt0, pluck(midi_hz(k - 12), e * EIGHTH * 1.8 + 0.3, 0.16))
            tt0 += e * EIGHTH

    # 写真〜紙：低いドローン
    dr_env = np.clip((t - M["photo"]) / 3, 0, 1) * np.clip((M["end"] - t) / 0.3, 0, 1)
    drone = np.sin(2 * np.pi * 55 * t) + 0.8 * np.sin(2 * np.pi * 55.9 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)
    mus += drone * dr_env * 0.07 * (1 + 1.2 * np.clip((t - M["paper"]) / (M["reveal"] - M["paper"]), 0, 1))

    # 赤丸：一つずつ琴の一音（だんだん低く）
    for k in range(len(LYRICS)):
        add(mus, M["circles"] + k * CIRCLE, pluck(BASE * 2 * (1 - 0.03 * k), 1.0, 0.18))
    # 種明かし：低い衝撃音＋不協和音
    m = int(3.0 * SR)
    tt = np.arange(m) / SR
    hit = np.sin(2 * np.pi * (34 + 50 * np.exp(-tt * 9)) * tt) * np.exp(-tt * 1.5)
    clu = sum(pluck(BASE * r, 3.0, 0.12) for r in (1.0, 16 / 15, 3 / 2 * 16 / 15))
    add(mus, M["reveal"], hit * 0.7 + clu)

    # オチ：祖母が妹に歌を教える声（ヒソヒソ声で遠くに）→ 「七つになる」の直前で途切れる
    h = np.concatenate([sing(SCORE[0][0], SING_WHISPER), sing(SCORE[1][0], SING_WHISPER)])
    h = 0.45 * h + 0.55 * fftconv(h, IR_HALL)[: len(h)]
    h = h[: int((M["last"] - M["end_hum"] + 0.1) * SR)]
    h[-int(0.15 * SR):] *= np.linspace(1, 0, int(0.15 * SR))
    add(mus, M["end_hum"], h, 0.3)
    # 振り向く：畳のきしみ → 灯りが消える
    m = int(0.5 * SR)
    tt = np.arange(m) / SR
    creak = np.sin(2 * np.pi * (180 + 40 * np.sin(2 * np.pi * 23 * tt)) * tt) * np.exp(-tt * 6) * (rng.random(m) < 0.3)
    add(mus, M["turn"] + 0.2, smooth(creak, 6), 0.4)
    m = int(0.25 * SR)
    add(mus, M["dark"], smooth(rng.standard_normal(m), 30) * np.exp(-np.arange(m) / SR * 15), 0.8)
    add(mus, M["dark"] + 0.5, pluck(BASE * 0.5, 2.0, 0.25))

    for st, sig in TLN.voice:
        add(voc, st, sig)
    venv = np.clip(smooth(np.abs(voc), 4000) * 6, 0, 1)
    mix = mus * (1 - 0.45 * venv) + voc * 0.9
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    mix = mix[: int(DUR * SR)]
    mix /= np.max(np.abs(mix)) / 0.92
    return (np.stack([mix, mix], axis=1) * 32767).astype(np.int16)


# ================================================================ 映像パーツ
def font(path, size):
    return ImageFont.truetype(path, size)


F_SUB = font(GOTHIC, 56)
F_TAG = font(GOTHIC, 40)
F_CREDIT = font(GOTHIC, 32)
F_TITLE = font(MINCHO, 76)
F_LYRIC = font(MINCHO, 72)
F_PAPER = font(MINCHO, 62)
F_REVEAL = font(MINCHO, 128)
F_REV_SIZES = {s: font(MINCHO, s) for s in range(62, 129)}

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = np.clip(1.3 - (((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.58)) ** 2) ** 1.1, 0, 1)[..., None]
SEPIA = np.array([1.08, 0.88, 0.64], np.float32)


def vtext(draw, x, y, text, fnt, fill, step=None):
    step = step or int(fnt.size * 1.12)
    cy = y
    for ch in text:
        if ch == "　":
            cy += step // 2
            continue
        bb = draw.textbbox((0, 0), ch, font=fnt)
        cw = bb[2] - bb[0]
        off = (fnt.size * 0.12, -fnt.size * 0.12) if ch in "っゃゅょぃ" else (0, 0)
        draw.text((x - cw / 2 + off[0], cy + off[1]), ch, font=fnt, fill=fill, stroke_width=3, stroke_fill=(20, 12, 8))
        cy += step


def kid(d, x, by, s, col=(14, 10, 8)):
    """着物におかっぱの子どもの影."""
    h = 230 * s
    d.polygon([(x - 46 * s, by), (x + 46 * s, by), (x + 26 * s, by - h * 0.62), (x - 26 * s, by - h * 0.62)], fill=col)
    hr = 32 * s
    hy = by - h * 0.62 - hr * 0.85
    d.ellipse([x - hr, hy - hr * 1.05, x + hr, hy + hr * 0.9], fill=col)
    d.rectangle([x - hr, hy - hr * 0.2, x + hr, hy + hr * 1.05], fill=col)


# ---------------------------------------------------------------- 夕暮れのあぜ道
P_NEAR = (430, 1760)
P_FAR = (690, 1040)
WELL = (760, 1028)


def paddy_bg():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    hz = 960
    for y in range(0, hz, 6):
        k = y / hz
        d.rectangle([0, y, W, y + 6], fill=(int(40 + 190 * k ** 1.6), int(28 + 110 * k ** 1.6), int(50 + 20 * k)))
    d.ellipse([230, 760, 370, 900], fill=(250, 205, 130))
    mt = [(0, 900)] + [(x, 880 - 70 * math.sin(x / 170) - 40 * math.sin(x / 61 + 1)) for x in range(0, W + 40, 40)] + [(W, 960), (0, 960)]
    d.polygon(mt, fill=(60, 38, 42))
    d.rectangle([0, hz, W, H], fill=(42, 34, 22))
    for i in range(26):          # 水田（空を映す）
        y = hz + 10 + (i ** 1.7) * 2.6
        d.rectangle([0, y, W, y + 3 + i * 0.9], fill=(int(150 - i * 3), int(90 - i * 2), int(55 - i)))
    d.polygon([(P_FAR[0] - 8, P_FAR[1] - 20), (P_FAR[0] + 14, P_FAR[1] - 20), (P_NEAR[0] + 230, H), (P_NEAR[0] - 260, H)],
              fill=(58, 46, 30))
    d.polygon([(WELL[0] + 40, 960), (W, 940), (W, 1120), (WELL[0] + 70, 1060)], fill=(30, 24, 20))   # 崖
    wx, wy = WELL
    d.rectangle([wx - 26, wy - 26, wx + 26, wy], fill=(36, 30, 26))                              # 井戸
    d.line([(wx - 22, wy - 26), (wx - 22, wy - 72)], fill=(30, 24, 20), width=4)
    d.line([(wx + 22, wy - 26), (wx + 22, wy - 72)], fill=(30, 24, 20), width=4)
    d.polygon([(wx - 36, wy - 70), (wx + 36, wy - 70), (wx, wy - 92)], fill=(30, 24, 20))
    d.line([(110, 1010), (100, 700)], fill=(26, 20, 18), width=16)                               # 木
    for k in range(10):
        d.line([(102, 740 + k * 18), (102 + (k % 2 * 2 - 1) * (45 + k * 7), 705 + k * 15)], fill=(26, 20, 18), width=6)
    return img


PADDY = paddy_bg()


def path_point(u):
    x = P_NEAR[0] + (P_FAR[0] - P_NEAR[0]) * u
    y = P_NEAR[1] + (P_FAR[1] - P_NEAR[1]) * u
    return x, y, 2.3 / (1 + u * 6.5)


def paddy_frame(t):
    img = PADDY.copy()
    d = ImageDraw.Draw(img)
    st = t - M["song"]
    li, lt = song_pos(st)
    if li <= 3:
        u = (li + lt) / 4 * 0.86
        kids = [(u, -1), (u, 1)]
    elif li == 4:
        kids = [(0.86, -1), (0.9, 0.4)]          # 一人がうしろに
    elif li == 5:
        kids = [(0.86, -1)]
    else:
        kids = [(0.86 - 0.62 * min(1, lt * 1.2), -1)]   # ひとりで帰ってくる
    if li >= 5:                                  # 井戸に蓋
        wx, wy = WELL
        d.rectangle([wx - 32, wy - 32, wx + 32, wy - 24], fill=(22, 18, 16))
    for u, side in kids:
        x, y, s = path_point(u)
        bob = math.sin(t * 7 + side) * 3 * s
        kid(d, x + side * 40 * s, y + bob, s * (1.0 if side < 0 else 0.86))
    if len(kids) == 2 and li <= 3:               # 手をつなぐ
        x, y, s = path_point(kids[0][0])
        d.line([(x - 22 * s, y - 120 * s), (x + 22 * s, y - 115 * s)], fill=(14, 10, 8), width=max(2, int(9 * s)))
    vtext(d, W - 130, 360, LYRICS[max(0, li)], F_LYRIC, (245, 236, 220))
    return img


# ---------------------------------------------------------------- 古い写真
def make_photo():
    img = Image.new("RGB", (W, H), (40, 28, 18))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(4)
    for y in range(0, H, 9):           # 木目の机
        c = int(40 + 10 * math.sin(y / 23) + r.uniform(-4, 4))
        d.line([(0, y), (W, y + r.uniform(-6, 6))], fill=(c, int(c * 0.7), int(c * 0.45)), width=6)
    ph = Image.new("RGB", (760, 980), (226, 218, 198))
    pd = ImageDraw.Draw(ph)
    for y in range(36, 830, 4):
        k = (y - 36) / 794
        pd.line([(36, y), (724, y)], fill=(int(150 - 50 * k),) * 3)
    pd.rectangle([36, 560, 724, 830], fill=(84, 80, 74))
    pd.rectangle([50, 330, 710, 560], fill=(70, 66, 62))
    pd.polygon([(20, 340), (740, 340), (630, 240), (130, 240)], fill=(52, 48, 44))
    for x in range(90, 700, 90):
        pd.line([(x, 340), (x, 560)], fill=(58, 54, 50), width=6)
    kid(pd, 300, 760, 2.0, col=(38, 36, 34))                        # 姉（祖母）
    kid(pd, 490, 770, 1.7, col=(38, 36, 34))                        # 妹
    pd.line([(330, 520), (460, 540)], fill=(38, 36, 34), width=16)
    for _ in range(70):                                             # 妹の顔だけ、ひっかいて消してある
        x0, y0 = 490 + r.uniform(-60, 60), 440 + r.uniform(-60, 60)
        pd.line([(x0, y0), (x0 + r.uniform(-50, 50), y0 + r.uniform(-50, 50))], fill=(232, 228, 216), width=int(r.uniform(2, 5)))
    pd.text((60, 870), "昭和二十四年　夏", font=font(MINCHO, 44), fill=(90, 70, 50))
    ph = ph.filter(ImageFilter.GaussianBlur(1.2)).rotate(4, expand=True, fillcolor=(0, 0, 0))
    mask = Image.new("L", (760, 980), 255).rotate(4, expand=True)
    img.paste(ph, ((W - ph.width) // 2, 430), mask)
    return img


PHOTO = make_photo()


# ---------------------------------------------------------------- 古い紙
PAPER_COLS = [W - 170 - i * 118 for i in range(len(LYRICS))]
PAPER_TOP = 380


def make_paper():
    base = np.full((H, W, 3), (222, 208, 176), np.float32)
    nz = np.asarray(Image.fromarray((rng.random((H // 4, W // 4)) * 255).astype(np.uint8)).resize((W, H)).filter(
        ImageFilter.GaussianBlur(6))).astype(np.float32)[..., None] / 255
    base *= 0.9 + 0.15 * nz
    stain = np.exp(-(((xx - 260) / 300) ** 2 + ((yy - 1500) / 260) ** 2))[..., None]
    base *= 1 - 0.18 * stain * np.array([0.6, 0.9, 1.4], np.float32)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(9)
    for _ in range(180):      # 和紙の繊維
        x, y = r.uniform(0, W), r.uniform(0, H)
        d.line([(x, y), (x + r.uniform(-30, 30), y + r.uniform(-30, 30))], fill=(200, 186, 152), width=1)
    targets = []
    for li, line in enumerate(LYRICS):
        x = PAPER_COLS[li]
        cy = PAPER_TOP + r.uniform(-8, 8)
        step = 74
        idx = 0
        for ch in line:
            if ch == "　":
                cy += step // 2
                continue
            ci = Image.new("L", (100, 100), 0)
            ImageDraw.Draw(ci).text((50, 50), ch, font=F_PAPER, fill=255, anchor="mm")
            ci = ci.rotate(r.uniform(-6, 6), resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.6))
            px = int(x - 50 + r.uniform(-4, 4))
            py = int(cy - 50 + 31 + r.uniform(-3, 3))
            img.paste(Image.new("RGB", (100, 100), (40, 30, 26)), (px, py), ci)
            if idx == 3:        # 数字の次の一文字
                targets.append((x, cy + 31, ch))
            idx += 1
            cy += step
    return img, targets


PAPER, TARGETS = make_paper()


# ---------------------------------------------------------------- 祖母の部屋
def room_frame(lamp=1.0, child_=False, eyes=0.0, turn=0.0):
    img = Image.new("RGB", (W, H), (int(22 * lamp + 2), int(16 * lamp + 2), int(10 * lamp + 2)))
    d = ImageDraw.Draw(img)
    sx0, sy0, sx1, sy1 = 120, 520, 960, 1260
    frame_c = (int(44 * lamp), int(30 * lamp), int(18 * lamp))
    d.rectangle([sx0, sy0, sx1, sy1], fill=(int(140 * lamp), int(104 * lamp), int(62 * lamp)))     # 障子
    for x in range(sx0, sx1 + 1, 105):
        d.line([(x, sy0), (x, sy1)], fill=frame_c, width=7)
    for y in range(sy0, sy1 + 1, 123):
        d.line([(sx0, y), (sx1, y)], fill=frame_c, width=7)
    d.rectangle([0, 1260, W, H], fill=(int(58 * lamp + 3), int(46 * lamp + 3), int(28 * lamp + 2)))  # 畳
    for y in (1360, 1520, 1740):
        d.line([(0, y), (W, y)], fill=(int(36 * lamp), int(28 * lamp), int(16 * lamp)), width=4)
    d.rectangle([780, 1080, 900, 1300], fill=(int(240 * lamp), int(196 * lamp), int(120 * lamp)))  # 行灯
    d.rectangle([772, 1070, 908, 1086], fill=(30, 22, 14))
    c = (10, 7, 5)
    gx = 420                                                           # 祖母（正座の影）
    d.ellipse([gx - 210, 1120, gx + 210, 1420], fill=c)
    d.polygon([(gx - 120, 1170), (gx + 120, 1170), (gx + 80, 930), (gx - 80, 930)], fill=c)
    hx = gx + 26 * (1 - turn)                                          # 妹の方 → こちらを向く
    d.ellipse([hx - 70, 770, hx + 70, 940], fill=c)
    d.ellipse([hx - 34 + 20 * (1 - turn), 718, hx + 34 + 20 * (1 - turn), 790], fill=c)   # 髷
    if eyes > 0:
        for s in (-1, 1):
            ex = hx + s * 26
            v = int(220 * eyes)
            d.ellipse([ex - 6, 846, ex + 6, 856], fill=(v, int(v * 0.95), int(v * 0.9)))
    if child_:
        kid(d, 660, 1330, 1.55, col=c)
    return img


# ---------------------------------------------------------------- 共通処理
def film(arr, t, sepia=1.0, dust=True):
    if sepia > 0:
        y = arr @ np.array([0.3, 0.59, 0.11], np.float32)
        arr = arr * (1 - sepia) + (y[..., None] * SEPIA) * sepia
    arr = arr * VIGNETTE * (1 - 0.05 * rng.random() - 0.02 * math.sin(t * 40))
    grain = rng.normal(0, 7, (H // 2, W // 2, 1)).astype(np.float32)
    arr = arr + np.repeat(np.repeat(grain, 2, 0), 2, 1)
    if dust:
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for _ in range(int(rng.integers(0, 5))):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            r = rng.uniform(1.5, 5)
            v = int(rng.choice([20, 230]))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(v, v, v))
        if rng.random() < 0.3:
            x = rng.uniform(80, W - 80)
            d.line([(x, 0), (x + rng.uniform(-20, 20), H)], fill=(200, 190, 170), width=1)
        arr = np.asarray(img).astype(np.float32)
    return arr


def overlay_text(img, t):
    d = ImageDraw.Draw(img)
    if t < M["dark"]:
        tag = "【意味がわかると怖い】"
        bb = d.textbbox((0, 0), tag, font=F_TAG)
        d.text(((W - (bb[2] - bb[0])) / 2, 150), tag, font=F_TAG, fill=(230, 60, 50), stroke_width=4, stroke_fill=(0, 0, 0))
        ttl = "祖母の数え歌"
        bb = d.textbbox((0, 0), ttl, font=F_TITLE)
        d.text(((W - (bb[2] - bb[0])) / 2, 205), ttl, font=F_TITLE, fill=(245, 240, 230), stroke_width=5, stroke_fill=(0, 0, 0))
    bb = d.textbbox((0, 0), CREDIT, font=F_CREDIT)
    d.text((W - (bb[2] - bb[0]) - 40, H - 330), CREDIT, font=F_CREDIT, fill=(200, 190, 175), stroke_width=3, stroke_fill=(0, 0, 0))
    for st, en, text in TLN.subs:
        if st <= t < en:
            a = max(0.0, min(1, (t - st) / 0.15, (en - t) / 0.2))
            lines = text.split("\n")
            y0 = 1440 - (len(lines) - 1) * 40
            for i, ln in enumerate(lines):
                bb = d.textbbox((0, 0), ln, font=F_SUB)
                d.text(((W - (bb[2] - bb[0])) / 2, y0 + i * 78), ln, font=F_SUB, fill=(int(245 * a),) * 3,
                       stroke_width=5, stroke_fill=(0, 0, 0))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def zoom_crop(img, z, cx=W / 2, cy=H / 2):
    if z <= 1.0001:
        return img.copy()
    nw, nh = int(W * z), int(H * z)
    big = img.resize((nw, nh), Image.BILINEAR)
    ox = int(min(max(cx * z - W / 2, 0), nw - W))
    oy = int(min(max(cy * z - H / 2, 0), nh - H))
    return big.crop((ox, oy, ox + W, oy + H))


# ================================================================ フレーム
def paper_frame(t):
    img = PAPER.copy()
    d = ImageDraw.Draw(img)
    for k, (x, y, ch) in enumerate(TARGETS):          # 赤丸を一つずつ描く
        p = (t - (M["circles"] + k * CIRCLE)) / 0.4
        if p > 0:
            d.arc([x - 52, y - 50, x + 52, y + 52], -100, -100 + 360 * min(1, p), fill=(176, 30, 26), width=7)
    if t < M["circles"]:
        return zoom_crop(img, 1.0 + 0.06 * (t - M["paper"]) / (M["circles"] - M["paper"]))
    if t < M["reveal"] - 0.2:
        return img
    p = ease((t - (M["reveal"] - 0.2)) / 0.6)            # 赤丸の字が抜け出して横一列に並ぶ
    img = Image.fromarray((np.asarray(img).astype(np.float32) * (1 - 0.72 * p)).astype(np.uint8))
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), HIDDEN, font=F_REVEAL)
    tw = bb[2] - bb[0]
    for k, ch in enumerate(HIDDEN):
        sx, sy, _ = TARGETS[k]
        pre = d.textbbox((0, 0), HIDDEN[:k], font=F_REVEAL)[2] if k else 0
        ex, ey = (W - tw) / 2 + pre + F_REVEAL.size / 2, 1000
        fs = F_REV_SIZES[int(62 + (128 - 62) * p)]
        d.text((sx + (ex - sx) * p, sy + (ey - sy) * p), ch, font=fs, fill=(int(176 + 40 * p), 24, 20), anchor="mm",
               stroke_width=int(3 * p), stroke_fill=(10, 0, 0))
    if p >= 1:
        img = zoom_crop(img, 1.0 + 0.04 * (t - M["reveal"] - 0.4))
    return img


def render_frame(fi):
    t = fi / FPS
    sepia, dust = 0.85, True
    if t < M["song"]:                                     # 0. つかみ：祖母の部屋
        img = zoom_crop(room_frame(lamp=0.25 + 0.75 * ease(t / 1.2)), 1.08 - 0.06 * t / M["song"])
    elif t < M["photo"]:                                  # 1. 数え歌
        img = zoom_crop(paddy_frame(t), 1.0 + 0.05 * (t - M["song"]) / (M["photo"] - M["song"]), W / 2, 1150)
    elif t < M["paper"]:                                  # 2. 写真
        p = (t - M["photo"]) / (M["paper"] - M["photo"])
        img = zoom_crop(PHOTO, 1.0 + 0.55 * ease(p), 560, 900 - 60 * p)
    elif t < M["end"]:                                    # 3. 紙
        sepia = 0.35
        img = paper_frame(t)
    elif t < M["dark"]:                                   # 4. オチ：祖母と妹
        turn = ease((t - M["turn"]) / 1.4) if t >= M["turn"] else 0.0
        eyes = ease((t - M["turn"] - 0.9) / 0.8) if t >= M["turn"] else 0.0
        lamp = 0.08 + 0.4 * (rng.random() < 0.4) if t >= M["dark"] - 0.35 else 1.0
        img = room_frame(lamp=lamp, child_=True, eyes=eyes, turn=turn)
        img = zoom_crop(img, 1.0 + 0.10 * ease((t - M["end"]) / (M["dark"] - M["end"])), 450, 950)
    else:                                                 # 暗転
        img = Image.new("RGB", (W, H))
        dust = False
    overlay_text(img, t)
    arr = film(np.asarray(img).astype(np.float32), t, sepia, dust)
    if M["reveal"] <= t < M["reveal"] + 0.12:             # 種明かしの瞬間に一瞬白く
        arr = arr * 0.4 + 150
    return np.clip(arr, 0, 255).astype(np.uint8)


def main():
    print("timeline:", {k: round(float(v), 2) for k, v in M.items()}, flush=True)
    wav_path = BUILD / "audio.wav"
    audio = make_audio()
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(audio.tobytes())
    if "--audio-only" in sys.argv:
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav_path),
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "8M", "-bufsize", "16M", "-tune", "grain",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    for fi in range(total):
        proc.stdin.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"  {fi}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done:", OUT)


if __name__ == "__main__":
    main()
