"""オリジナル曲「ミライシグナル」を合成し、音源とカラオケ字幕(ASS)を出力する。
BPM128 / 4/4 / Key C。依存: numpy のみ。
"""
import json, sys, wave
import numpy as np

SR = 44100
BPM = 128
BEAT = 60 / BPM
BAR = BEAT * 4
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

# ---- 構成とコード ----------------------------------------------------------
C, Dm, Em, F, G, Am = ([48,52,55],[50,53,57],[52,55,59],[53,57,60],[55,59,62],[57,60,64])
sections = [  # (名前, コード(1小節ずつ), ドラム強度)
    ("intro",  [F,G,Em,Am], 1),
    ("A",      [Am,F,C,G, Am,F,C,G], 1),
    ("B",      [Dm,Em,F,G], 2),
    ("S1",     [F,G,Em,Am, F,G,Em,Am], 3),
    ("S2",     [F,G,Em,Am, F,G,Em,Am], 3),
    ("outro",  [F,G,C,C], 1),
]
bars = []
for name, chords, lv in sections:
    for ch in chords: bars.append((name, ch, lv))
NBARS = len(bars)
TOTAL = NBARS * BAR + 3.0
N = int(TOTAL * SR)

# ---- メロディ(歌詞チャンク, [(midi or None, 拍)]) -----------------------------
E4,F4,G4,A4,B4,C5,D5,E5,D4 = 64,65,67,69,71,72,74,76,62
R = None
def L(*items): return list(items)
melody = {  # 開始小節 -> 1行(2小節=8拍)
 4:  L(("",[(R,.5)]),("眠",[(E4,.5),(E4,.5)]),("れ",[(G4,.5)]),("な",[(A4,.5)]),("い",[(A4,.5)]),("夜",[(G4,.5),(E4,.5)]),("に",[(D4,1.5)]),("",[(R,2.5)])),
 6:  L(("",[(R,.5)]),("光",[(E4,.5),(G4,.5)]),("る",[(A4,.5)]),("ス",[(C5,.5)]),("マ",[(C5,.5)]),("ホ",[(B4,.5)]),("の",[(A4,.5)]),("灯",[(G4,.5),(A4,.5)]),("り",[(G4,1.5)]),("",[(R,1.5)])),
 8:  L(("",[(R,.5)]),("誰",[(A4,.5),(A4,.5)]),("か",[(G4,.5)]),("の",[(A4,.5)]),("声",[(C5,.5),(B4,.5)]),("を",[(A4,.5)]),("探",[(G4,.5),(A4,.5)]),("し",[(G4,.5)]),("て",[(E4,1)]),("",[(R,1.5)])),
 10: L(("",[(R,.5)]),("小",[(E4,.5),(G4,.5)]),("さ",[(A4,.5)]),("く",[(G4,.5)]),("歌",[(E4,.5),(D4,.5)]),("って",[(E4,.5)]),("た",[(D4,2)]),("",[(R,2)])),
 12: L(("",[(R,.5)]),("届",[(F4,.5),(F4,.5)]),("か",[(G4,.5)]),("な",[(A4,.5)]),("く",[(A4,.5)]),("て",[(G4,.5)]),("も",[(A4,.5)]),("い",[(B4,.5)]),("い",[(C5,.5)]),("か",[(B4,.5)]),("ら",[(G4,1)]),("",[(R,1.5)])),
 14: L(("",[(R,.5)]),("今 ",[(A4,.5),(B4,.5)]),("声",[(C5,.5),(C5,.5)]),("に",[(D5,.5)]),("し",[(C5,.5)]),("て",[(D5,.5)]),("み",[(E5,.5)]),("た",[(D5,.5)]),("い",[(D5,2)]),("",[(R,1)])),
}
chorus1 = [
 L(("響",[(E5,.5),(E5,.5)]),("け ",[(D5,1)]),("ミ",[(C5,.5)]),("ラ",[(D5,.5)]),("イ",[(E5,.5)]),("シ",[(D5,.5)]),("グ",[(C5,.5)]),("ナ",[(B4,.5)]),("ル",[(D5,1.5)]),("",[(R,1.5)])),
 L(("こ",[(B4,.5)]),("の",[(C5,.5)]),("歌",[(D5,1),(C5,.5)]),("が",[(B4,.5)]),("届",[(G4,.5),(A4,.5)]),("く",[(C5,.5)]),("ま",[(B4,.5)]),("で",[(A4,2)]),("",[(R,1)])),
 L(("眠",[(E5,.5),(E5,.5)]),("ら",[(D5,.5)]),("な",[(C5,.5)]),("い",[(D5,.5)]),("夜",[(E5,.5),(E5,.5)]),("を",[(D5,.5)]),("越",[(C5,.5),(D5,.5)]),("え",[]),("て",[(B4,1.5)]),("",[(R,1.5)])),
 L(("朝",[(B4,.5),(C5,.5)]),("ま",[(D5,1)]),("で",[(E5,1)]),("歌",[(D5,.5),(C5,.5)]),("う",[(B4,.5)]),("よ",[(A4,3)]),("",[(R,.5)])),
]
# 「越え」を1チャンクにまとめる
chorus1[2] = L(("眠",[(E5,.5),(E5,.5)]),("ら",[(D5,.5)]),("な",[(C5,.5)]),("い",[(D5,.5)]),("夜",[(E5,.5),(E5,.5)]),("を",[(D5,.5)]),("越え",[(C5,.5),(D5,.5)]),("て",[(B4,1.5)]),("",[(R,1.5)]))
def relyric(line, chunks):
    notes = [n for _, ns in line for n in ns if n[0] is not None]
    out, i = [], 0
    if line[0][1][0][0] is None: out.append(("", [line[0][1][0]]))
    for text, k in chunks:
        out.append((text, notes[i:i+k])); i += k
    rest = [n for n in line[-1][1] if n[0] is None]
    if rest: out.append(("", rest))
    assert i == len(notes), (chunks, i, len(notes))
    return out
chorus2 = [
 chorus1[0],
 relyric(chorus1[1], [("こ",1),("の",1),("声",2),("が",1),("届",2),("く",1),("ま",1),("で",1)]),
 relyric(chorus1[2], [("泣",1),("い",1),("て",1),("た",1),("昨",1),("日",2),("を",1),("越え",2),("て",1)]),
 relyric(chorus1[3], [("笑",2),("顔",1),("で",1),("歌",2),("う",1),("よ",1)]),
]
for i, ln in enumerate(chorus1): melody[16 + 2*i] = ln
for i, ln in enumerate(chorus2): melody[24 + 2*i] = ln
for b, ln in melody.items():
    tot = sum(d for _, ns in ln for _, d in ns)
    assert abs(tot - 8) < 1e-9, (b, tot)

# ---- 音源合成 ---------------------------------------------------------------
rng = np.random.default_rng(7)
def env(n, a, d, s, r):
    e = np.ones(n) * s
    a, d, r = int(a*SR), int(d*SR), int(r*SR)
    a = min(a, n); e[:a] = np.linspace(0, 1, a)
    d2 = min(d, n - a); e[a:a+d2] = np.linspace(1, s, d2)
    r = min(r, n); e[n-r:] *= np.linspace(1, 0, r)
    return e
def add(buf, start, sig):
    i = int(start * SR); j = min(i + len(sig), len(buf))
    if i < len(buf): buf[i:j] += sig[:j-i]
def saw(f, t): return 2 * ((f * t) % 1) - 1

drums, bass, pad, arp, lead = (np.zeros(N) for _ in range(5))

kick_t = np.arange(int(.35*SR)) / SR
KICK = np.sin(2*np.pi*(45*kick_t + 90*(1-np.exp(-kick_t*30))/30)) * np.exp(-kick_t*9)
sn_t = np.arange(int(.25*SR)) / SR
SNARE = (rng.uniform(-1,1,len(sn_t))*.7 + np.sin(2*np.pi*190*sn_t)*.5) * np.exp(-sn_t*18)
hh_t = np.arange(int(.06*SR)) / SR
HAT = np.diff(rng.uniform(-1,1,len(hh_t)+1)) * np.exp(-hh_t*70) * .5

for bi, (name, ch, lv) in enumerate(bars):
    t0 = bi * BAR
    last = bi == NBARS - 1
    # ドラム
    if not last:
        kicks = [0,1,2,3] if lv == 3 else ([0,2,2.5] if lv == 2 else [0,2])
        for k in kicks: add(drums, t0 + k*BEAT, KICK)
        if lv >= 2 or name in ("A",):
            for s in [1,3]: add(drums, t0 + s*BEAT, SNARE * (1 if lv>=2 else .7))
        if name == "intro" and bi < 2: pass
        for h in np.arange(0, 4, .5): add(drums, t0 + h*BEAT, HAT * (1 if h % 1 else .6))
        if name == "B" and bi % 4 == 3:  # サビ前フィル
            for k in np.arange(2, 4, .25): add(drums, t0 + k*BEAT, SNARE*.6)
    # ベース(8分)
    root = ch[0] - 12
    steps = [0] if last else np.arange(0, 4, .5)
    for s in steps:
        dur = BAR if last else BEAT*.45
        n = int(dur*SR); t = np.arange(n)/SR; f = mtof(root)
        sig = (np.sin(2*np.pi*f*t) + .35*saw(f, t)) * env(n, .005, .08, .6, .03)
        add(bass, t0 + s*BEAT, sig * .5)
    # パッド
    dur = BAR * (2.5 if last else 1); n = int(dur*SR); t = np.arange(n)/SR
    sig = sum(saw(mtof(m)*1.003, t) + saw(mtof(m)*.997, t) for m in ch) / 6
    add(pad, t0, sig * env(n, .08, .2, .8, .3) * .35)
    # アルペジオ(16分)
    if lv >= 2 or name == "intro":
        notes = [m + 12 for m in ch] + [ch[0] + 24]
        for k in range(0 if not last else 0, 1 if last else 16):
            m = notes[[0,1,2,3,2,1,0,1][k % 8]]
            n = int(BEAT*.25*SR); t = np.arange(n)/SR
            add(arp, t0 + k*BEAT/4, np.sign(np.sin(2*np.pi*mtof(m)*t)) * np.exp(-t*25) * .12)

# ガイドメロディ(ボカロ風リード)
lyrics_lines = []
for b in sorted(melody):
    t = b * BAR; line = []
    for text, ns in melody[b]:
        st = t
        for m, d in ns:
            if m is not None:
                n = int((d*BEAT*.95)*SR); tt = np.arange(n)/SR
                vib = 1 + .006*np.sin(2*np.pi*5.5*tt) * np.clip(tt*4, 0, 1)
                ph = np.cumsum(mtof(m)*vib) / SR
                sig = (np.sign(np.sin(2*np.pi*ph))*.3 + saw(1, ph)*.5 + np.sin(2*np.pi*ph)*.5)
                add(lead, t, sig * env(n, .01, .05, .8, .04) * .28)
            t += d*BEAT
        line.append((text, st, t))
    lyrics_lines.append(line)

def norm_mix(parts):
    m = sum(parts)
    # 簡易ステレオ:アルペジオ左寄り・パッド右寄り
    L_ = m + arp*.4 - pad*.15; R_ = m - arp*.4 + pad*.15
    st = np.stack([L_, R_], 1)
    st = np.tanh(st * 1.2)
    return st / np.max(np.abs(st)) * .89
def write(path, st):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())

inst = [drums*.9, bass, pad, arp]
write(f"{OUT}/mirai_signal_offvocal.wav", norm_mix(inst))
write(f"{OUT}/mirai_signal_guide.wav", norm_mix(inst + [lead]))

# ---- カラオケ字幕(ASS) ------------------------------------------------------
def ts(s):
    s = max(0, s); h = int(s//3600); m = int(s%3600//60); return f"{h}:{m:02d}:{s%60:05.2f}"
ass = ["[Script Info]","ScriptType: v4.00+","PlayResX: 1920","PlayResY: 1080","",
"[V4+ Styles]",
"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
"Style: Lyric,IPAPGothic,96,&H0066E0FF,&H00FFFFFF,&H00402010,&H80000000,1,0,0,0,100,100,4,0,1,6,3,2,60,60,170,1",
"Style: Next,IPAPGothic,58,&H00E0D0C0,&H00E0D0C0,&H00402010,&H80000000,1,0,0,0,100,100,2,0,1,4,0,2,60,60,80,1",
"Style: Title,IPAPGothic,150,&H00FFFFFF,&H00FFFFFF,&H00A03070,&H80000000,1,0,0,0,100,100,10,0,1,8,4,5,60,60,0,1",
"Style: Sub,IPAPGothic,56,&H00FFF0F8,&H00FFFFFF,&H00A03070,&H80000000,1,0,0,0,100,100,6,0,1,4,2,5,60,60,0,1",
"","[Events]","Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
ass.append(f"Dialogue: 0,{ts(0.3)},{ts(4*BAR-1.0)},Title,,0,0,0,,{{\\fad(600,500)\\pos(960,470)}}ミライシグナル")
ass.append(f"Dialogue: 0,{ts(0.8)},{ts(4*BAR-1.0)},Sub,,0,0,0,,{{\\fad(600,500)\\pos(960,620)}}Original Song / 歌ってみた")
prev_end = 4*BAR - 1.0
for i, line in enumerate(lyrics_lines):
    start = max(prev_end, line[0][1] - 1.2); end = [c for c in line if c[0]][-1][2] + .4
    sung = [c for c in line if c[0]]
    lead_in = sung[0][1] - start
    prev_end = end
    text = "".join(f"{{\\k{max(1, round((e - s)*100))}}}{tx}" for tx, s, e in sung)
    ass.append(f"Dialogue: 0,{ts(start)},{ts(end)},Lyric,,0,0,0,,{{\\fad(150,150)\\k{round(lead_in*100)}}}{text}")
    if i + 1 < len(lyrics_lines):
        nxt = "".join(tx for tx, _, _ in lyrics_lines[i+1])
        ass.append(f"Dialogue: 0,{ts(start)},{ts(end)},Next,,0,0,0,,{{\\fad(150,150)}}{nxt}")
oT = 32 * BAR
ass.append(f"Dialogue: 0,{ts(oT+.3)},{ts(TOTAL-.2)},Title,,0,0,0,,{{\\fad(600,800)\\pos(960,470)\\fs110}}Thank you for listening!")
ass.append(f"Dialogue: 0,{ts(oT+.8)},{ts(TOTAL-.2)},Sub,,0,0,0,,{{\\fad(600,800)\\pos(960,610)}}高評価・チャンネル登録よろしくね♪")
open(f"{OUT}/lyrics_karaoke.ass", "w", encoding="utf-8").write("\n".join(ass) + "\n")
json.dump({"duration": TOTAL, "bpm": BPM}, open(f"{OUT}/meta.json", "w"))
print("ok", round(TOTAL, 2), "sec")
