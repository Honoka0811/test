# -*- coding: utf-8 -*-
"""最小限の標準MIDIファイル(SMF)パーサ。外部ライブラリ不要。
read(path) -> (notes, ppq)   notes: [(start_tick, dur_tick, pitch, velocity, track)]"""
import struct

def _vlq(b, i):
    v = 0
    while True:
        c = b[i]; i += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80: return v, i

def read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'MThd'
    _, ntrk, ppq = struct.unpack('>HHH', b[8:14])
    i = 14; notes = []; tempos = []
    for tr in range(ntrk):
        assert b[i:i + 4] == b'MTrk'
        ln = struct.unpack('>I', b[i + 4:i + 8])[0]
        j, end = i + 8, i + 8 + ln
        t = 0; run = None; on = {}
        while j < end:
            d, j = _vlq(b, j); t += d
            st = b[j]
            if st & 0x80: j += 1; run = st if st < 0xF0 else run
            else: st = run
            if st == 0xFF:
                typ = b[j]; ln2, j = _vlq(b, j + 1)
                if typ == 0x51: tempos.append((t, int.from_bytes(b[j:j + 3], 'big')))
                j += ln2
            elif st in (0xF0, 0xF7):
                ln2, j = _vlq(b, j); j += ln2
            else:
                hi = st & 0xF0
                n = 1 if hi in (0xC0, 0xD0) else 2
                a = b[j:j + n]; j += n
                if hi == 0x90 and a[1] > 0: on[a[0]] = (t, a[1])
                elif hi in (0x80, 0x90) and a[0] in on:
                    s, v = on.pop(a[0]); notes.append((s, t - s, a[0], v, tr))
        i = end
    return sorted(notes), ppq, tempos
