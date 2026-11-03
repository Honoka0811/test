# -*- coding: utf-8 -*-
"""BGM: パッヘルベル「カノン」(パブリックドメイン)のポップ・アレンジを GM 音源で演奏して合成する。
ニ長調 / 100BPM、2拍ごとにコードが進む。ピアノのアルペジオ + ピチカート低音 + ストリングスのパッド
+ フルート/グロッケンの旋律(カノンの各変奏) + 軽いポップ系ドラム + 簡易リバーブ。
音源: GeneralUser GS (SoundFont, 自由に利用可) を tinysoundfont でレンダリング。
単体実行: python3 bgm.py [秒数] [出力wav]
環境変数 SF2: SoundFont のパス(既定 /home/user/assets/sf2/GeneralUser-GS.sf2)
"""
import os, sys, wave
import numpy as np
import tinysoundfont as tsf

SR = 48000
BPM = 100
BEAT = 60.0 / BPM
SLOT = BEAT * 2                      # 1コード = 2拍
SF2 = os.environ.get('SF2', '/home/user/assets/sf2/GeneralUser-GS.sf2')

# 音名 → MIDI
def n(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return names[name[:-1]] + 12 * (int(name[-1]) + 1)

# カノンの定旋律(低音)と和音: D A Bm F#m G D G A
BASS = [n('D3'), n('A2'), n('B2'), n('F#2'), n('G2'), n('D2'), n('G2'), n('A2')]
CHORDS = [['D4', 'F#4', 'A4'], ['C#4', 'E4', 'A4'], ['D4', 'F#4', 'B4'], ['C#4', 'F#4', 'A4'],
          ['D4', 'G4', 'B4'], ['D4', 'F#4', 'A4'], ['D4', 'G4', 'B4'], ['C#4', 'E4', 'A4']]
CHORDS = [[n(x) for x in c] for c in CHORDS]
# 旋律の変奏(1コードあたりの音数が 1 / 1 / 4 / 8)
V1 = ['F#5', 'E5', 'D5', 'C#5', 'B4', 'A4', 'B4', 'C#5']
V2 = ['D5', 'C#5', 'B4', 'A4', 'G4', 'F#4', 'G4', 'E4']
V3 = ['D4 F#4 A4 G4', 'F#4 D4 F#4 E4', 'D4 B3 D4 A4', 'G4 B4 A4 G4',
      'F#4 D4 E4 C#5', 'D5 F#5 A5 A4', 'B4 G4 A4 F#4', 'D5 D5 D5 C#5']
V4 = ['D5 C#5 D5 D4 C#4 A4 E4 F#4', 'D4 D5 C#5 B4 C#5 F#5 A5 B5', 'G5 F#5 E5 G5 F#5 E5 D5 C#5', 'B4 A4 G4 F#4 E4 G4 F#4 E4',
      'D4 E4 F#4 G4 A4 E4 A4 G4', 'F#4 B4 A4 G4 A4 G4 F#4 E4', 'D4 B3 B4 C#5 D5 C#5 B4 A4', 'G4 F#4 E4 B4 A4 B4 A4 G4']

# GM プログラム
PIANO, BASS_PZ, PAD, FLUTE, GLOCK, STR_HI = 0, 45, 49, 73, 9, 48
CH = {'piano': 0, 'bass': 1, 'pad': 2, 'lead': 3, 'glock': 4, 'str': 5, 'drum': 9}

def build_events(total):
    """(time, kind, ch, key, vel, dur) のリスト"""
    ev = []
    def note(t, ch, key, vel, dur):
        if t < total: ev.append((t, ch, key, vel, dur))
    cycles = int(np.ceil(total / (SLOT * 8))) + 1
    for c in range(cycles):
        t0 = c * SLOT * 8
        for i in range(8):
            ts = t0 + i * SLOT
            chord, bass = CHORDS[i], BASS[i]
            # ピアノ: アルペジオ(8分) root-5th-3rd(上)-5th、最後の周回は和音でゆったり
            arp = [bass + 12, chord[2], chord[1] + 12, chord[2]] if c % 2 == 0 else [bass + 12, chord[1], chord[2], chord[1] + 12]
            for k, key in enumerate(arp):
                note(ts + k * BEAT / 2, CH['piano'], key, 62 + (10 if k == 0 else 0), BEAT * 0.9)
            # ピチカート低音: 1拍目と2拍目裏
            note(ts, CH['bass'], bass, 92, BEAT * 1.2)
            if c >= 1: note(ts + BEAT * 1.5, CH['bass'], bass + 12, 70, BEAT * 0.5)
            # パッド: 和音を保持(2周目以降)
            if c >= 1:
                for key in chord: note(ts, CH['pad'], key, 42, SLOT * 1.02)
            # ドラム(2周目以降、軽め)
            if c >= 1:
                d = CH['drum']
                note(ts, d, 36, 78, 0.2)                              # キック
                note(ts + BEAT, d, 37, 70, 0.2)                        # サイドスティック
                for k in range(4): note(ts + k * BEAT / 2, d, 42, 48 + (12 if k % 2 == 0 else 0), 0.1)  # ハイハット
                for k in range(4): note(ts + k * BEAT / 2 + BEAT / 4, d, 82, 34, 0.08)                 # シェイカー
                if i == 7: note(ts + BEAT * 1.5, d, 38, 52, 0.2)       # 周回の終わりに軽いスネア
            # 旋律の変奏を周回ごとに切り替え
            var = c % 7
            def melody(line, ch, vel, oct=0):
                keys = [n(x) + oct for x in line[i].split()]
                step = SLOT / len(keys)
                for k, key in enumerate(keys):
                    note(ts + k * step, ch, key, vel + (6 if k == 0 else 0), step * 0.95)
            if var == 1: melody(V1, CH['glock'], 70, 12); melody(V1, CH['lead'], 72)
            elif var == 2: melody(V2, CH['lead'], 76); melody(V2, CH['glock'], 58, 12)
            elif var == 3: melody(V3, CH['lead'], 78)
            elif var == 4: melody(V4, CH['lead'], 80)
            elif var == 5: melody(V1, CH['str'], 70, 0); melody(V2, CH['str'], 62, 0); melody(V1, CH['glock'], 60, 12)
            elif var == 6: melody(V3, CH['lead'], 80); melody(V1, CH['str'], 60, 0)
    ev.sort(key=lambda e: e[0])
    return ev

def reverb(x, mix=0.22):
    """簡易シュレーダー・リバーブ(コム4本 + オールパス2本)。x: (N,2)"""
    y = np.zeros_like(x)
    for D, g in ((1557, 0.805), (1617, 0.827), (1491, 0.783), (1422, 0.764)):
        buf = np.zeros_like(x)
        nblk = int(np.ceil(len(x) / D))
        for b in range(nblk):
            s, e = b * D, min((b + 1) * D, len(x))
            buf[s:e] = x[s:e] + (g * buf[s - D:e - D] if b else 0)
        y += buf
    y /= 4
    for D, g in ((225, 0.7), (556, 0.7)):
        out = np.zeros_like(y)
        nblk = int(np.ceil(len(y) / D))
        for b in range(nblk):
            s, e = b * D, min((b + 1) * D, len(y))
            prev = out[s - D:e - D] if b else 0
            out[s:e] = -g * y[s:e] + (y[s - D:e - D] if b else 0) + g * prev
        y = out
    return x * (1 - mix) + y * mix

def generate(total):
    synth = tsf.Synth(samplerate=SR, gain=-6.0)
    sf = synth.sfload(SF2)
    for name, prog in (('piano', PIANO), ('bass', BASS_PZ), ('pad', PAD), ('lead', FLUTE), ('glock', GLOCK), ('str', STR_HI)):
        synth.program_select(CH[name], sf, 0, prog)
    synth.program_select(CH['drum'], sf, 128, 0, is_drums=True)
    for ch, pan in ((0, 54), (1, 64), (2, 64), (3, 76), (4, 88), (5, 44), (9, 64)):
        synth.control_change(ch, 10, pan)
    synth.control_change(CH['pad'], 7, 80); synth.control_change(CH['str'], 7, 90)
    events = build_events(total + 4)
    offs = []  # (time, ch, key)
    N = int((total + 4) * SR)
    out = np.zeros((N, 2), dtype=np.float32)
    block = 480
    ei = 0
    for s in range(0, N, block):
        tnow = s / SR
        while ei < len(events) and events[ei][0] <= tnow:
            t, ch, key, vel, dur = events[ei]; ei += 1
            synth.noteon(ch, key, vel); offs.append((t + dur, ch, key))
        if offs:
            keep = []
            for o in offs:
                if o[0] <= tnow: synth.noteoff(o[1], o[2])
                else: keep.append(o)
            offs = keep
        buf = synth.generate_simple(min(block, N - s))
        out[s:s + min(block, N - s)] = np.frombuffer(buf, dtype=np.float32).reshape(-1, 2)
    out = reverb(out)
    # 終端フェード
    n_total = int(total * SR)
    out = out[:n_total]
    fade = int(2.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    out = out / (np.max(np.abs(out)) or 1) * 0.9
    return out.astype(np.float32)

def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    sec = float(sys.argv[1]) if len(sys.argv) > 1 else 70.0
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'bgm.wav')
    write_wav(dst, generate(sec)); print('wrote', dst)
