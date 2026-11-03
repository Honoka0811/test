# -*- coding: utf-8 -*-
"""BGM: J.S. Bach, Prelude in C major BWV 846 (public domain) -> MIDI -> piano WAV via FluidSynth.
usage: python3 bgm_bach.py out.wav [sample_rate] [bpm]
"""
import subprocess, sys, os
import mido

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
def n(name):  # e.g. "C4", "F#4", "Bb3"
    p = NOTE[name[0]]; i = 1
    if name[1] == "#": p += 1; i = 2
    elif name[1] == "b": p -= 1; i = 2
    return 12 * (int(name[i:]) + 1) + p

# bars 1-32: five notes, played as n1 n2 n3 n4 n5 n3 n4 n5 (twice per bar)
BARS = [
    "C4 E4 G4 C5 E5", "C4 D4 A4 D5 F5", "B3 D4 G4 D5 F5", "C4 E4 G4 C5 E5",
    "C4 E4 A4 E5 A5", "C4 D4 F#4 A4 D5", "B3 D4 G4 D5 G5", "B3 C4 E4 G4 C5",
    "A3 C4 E4 G4 C5", "D3 A3 D4 F#4 C5", "G3 B3 D4 G4 B4", "G3 Bb3 E4 G4 C#5",
    "F3 A3 D4 A4 D5", "F3 Ab3 D4 F4 B4", "E3 G3 C4 G4 C5", "E3 F3 A3 C4 F4",
    "D3 F3 A3 C4 F4", "G2 D3 G3 B3 F4", "C3 E3 G3 C4 E4", "C3 G3 Bb3 C4 E4",
    "F2 F3 A3 C4 E4", "F#2 C3 A3 C4 Eb4", "Ab2 F3 B3 C4 D4", "G2 F3 G3 B3 D4",
    "G2 E3 G3 C4 E4", "G2 D3 G3 C4 F4", "G2 D3 G3 B3 F4", "G2 Eb3 A3 C4 F#4",
    "G2 E3 G3 C4 G4", "G2 D3 G3 C4 F4", "G2 D3 G3 B3 F4", "C2 C3 G3 Bb3 E4",
]
# bars 33-34: bass note held, then 14 sixteenth notes
CODA = [
    ("C2 C3", "F3 A3 C4 F4 C5 A4 C5 A4 F4 A4 F4 D4 F4 D4"),
    ("C2 B2", "G4 B4 D5 F5 D5 B4 D5 B4 G4 B4 D4 F4 E4 D4"),
]
FINAL = "C2 C3 E4 G4 C5"

def build_midi(path, bpm=66):
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)))
    tr.append(mido.Message("program_change", program=0, time=0))  # acoustic grand piano
    s = 120  # sixteenth note in ticks
    events = []  # (tick, msg)
    t = 0
    def add(tick, notes, dur, vel):
        for p in notes:
            events.append((tick, mido.Message("note_on", note=p, velocity=vel)))
            events.append((tick + dur, mido.Message("note_off", note=p, velocity=0)))
    def pedal(tick):  # lift and re-press the sustain pedal at each bar so harmonies stay clean
        events.append((max(tick - 10, 0), mido.Message("control_change", control=64, value=0)))
        events.append((tick, mido.Message("control_change", control=64, value=127)))
    for bar in BARS:
        pedal(t)
        p = [n(x) for x in bar.split()]
        seq = [p[0], p[1], p[2], p[3], p[4], p[2], p[3], p[4]] * 2
        for k, pitch in enumerate(seq):
            vel = 68 if k % 8 == 0 else (58 if k % 4 == 0 else 50)
            add(t + k * s, [pitch], s * 3, vel)
        t += 16 * s
    for bass, run in CODA:
        pedal(t)
        add(t, [n(x) for x in bass.split()], 16 * s, 66)
        for k, x in enumerate(run.split()):
            add(t + (k + 2) * s, [n(x)], s * 3, 56 if k else 60)
        t += 16 * s
    pedal(t)
    add(t, [n(x) for x in FINAL.split()], 16 * s * 2, 64)
    t += 16 * s * 2
    events.sort(key=lambda e: (e[0], {"note_off": 0, "control_change": 1}.get(e[1].type, 2)))
    last = 0
    for tick, msg in events:
        msg.time = tick - last; last = tick
        tr.append(msg)
    mid.save(path)
    return t / 480 * 60 / bpm  # seconds

if __name__ == "__main__":
    out = sys.argv[1]; sr = int(sys.argv[2]) if len(sys.argv) > 2 else 48000; bpm = int(sys.argv[3]) if len(sys.argv) > 3 else 66
    mid = out + ".mid"
    secs = build_midi(mid, bpm)
    subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.6", "-r", str(sr), "-F", out, "/usr/share/sounds/sf2/FluidR3_GM.sf2", mid], check=True)
    print(f"bgm {out} {secs:.1f}s")
