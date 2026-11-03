"""Upbeat pop/lo-fi arrangement of Pachelbel's Canon in D (public domain) -> MIDI."""
import mido, sys, random
from mido import Message, MidiFile, MidiTrack, MetaMessage
random.seed(7)
OUT = sys.argv[1]
BPM = 108; TPB = 480
mid = MidiFile(ticks_per_beat=TPB)
def N(name):  # 'F#5' -> midi
    names = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    oct_ = int(name[-1]); return 12*(oct_+1) + names[name[:-1]]
# ground: 8 chords, 2 beats each -> 16 beats per cycle
CHORDS = [('D',['D','F#','A']), ('A',['A','C#','E']), ('B',['B','D','F#']), ('F#',['F#','A','C#']),
          ('G',['G','B','D']), ('D',['D','F#','A']), ('G',['G','B','D']), ('A',['A','C#','E'])]
BEAT = TPB; E = TPB//2; S16 = TPB//4
events = {}  # channel -> list of (tick, msg)
def add(ch, tick, note, vel, dur):
    tick = int(round(tick)); dur = int(round(dur))
    events.setdefault(ch, []).append((tick, Message('note_on', note=note, velocity=vel, channel=ch, time=0)))
    events.setdefault(ch, []).append((tick+dur, Message('note_off', note=note, velocity=0, channel=ch, time=0)))
def pitch(name, octv): return N(f'{name}{octv}')
# chord tones in a given octave for comp: root in oct 4 region, keep voicings tight (E4..A5)
def voicing(tones, low=N('E4')):
    out = []
    for t in tones:
        p = pitch(t, 4)
        while p < low: p += 12
        out.append(p)
    return sorted(out)

NCYC = 9
CYC = 16*BEAT
# melodic lines (per cycle, as list of (start_beat, dur_beats, note))
lineA = [(i*2, 2, n) for i, n in enumerate(['F#5','E5','D5','C#5','B4','A4','B4','C#5'])]
lineA2 = [(i*2, 2, n) for i, n in enumerate(['D5','C#5','B4','A4','G4','F#4','G4','E4'])]
lineB_notes = ['D4','F#4','A4','G4','F#4','D4','F#4','E4','D4','B3','D4','A4','G4','B4','A4','G4',
               'F#4','D4','E4','C#5','D5','F#5','A5','A4','B4','G4','A4','F#4','D4','D5','D5','C#5']
lineB = [(i*0.5, 0.5, n) for i, n in enumerate(lineB_notes)]
# my own eighth-note arpeggio variation (chord tones + passing), per chord 4 eighths
def lineC():
    out = []
    pats = [['A5','F#5','D5','F#5'], ['E5','C#5','A4','C#5'], ['F#5','D5','B4','D5'], ['C#5','A4','F#4','A4'],
            ['D5','B4','G4','B4'], ['F#5','D5','A4','D5'], ['G5','D5','B4','D5'], ['E5','C#5','A4','E5']]
    for ci, p in enumerate(pats):
        for k, n in enumerate(p): out.append((ci*2 + k*0.5, 0.5, n))
    return out
# syncopated hook (quarter-note thirds, upper), used on glock
lineD = []
for ci, (root, tones) in enumerate(CHORDS):
    v = voicing(tones, N('A4'))
    lineD += [(ci*2, 1.0, v[2]), (ci*2+1, 0.5, v[1]), (ci*2+1.5, 0.5, v[0])]

PIANO, PIZZ, PAD, GLOCK, EPIANO, BASS = 0, 1, 2, 3, 4, 5
progs = {PIANO: 0, PIZZ: 45, PAD: 48, GLOCK: 9, EPIANO: 4, BASS: 32}
def play_line(ch, cyc, line, vel, legato=0.95, octshift=0):
    base = cyc*CYC
    for sb, db, n in line:
        p = (N(n) if isinstance(n, str) else n) + octshift
        add(ch, base + int(sb*BEAT), p, vel + random.randint(-6, 6), int(db*BEAT*legato))
for cyc in range(NCYC):
    base = cyc*CYC
    last = (cyc == NCYC-1)
    intro = (cyc == 0)
    full = cyc >= 2
    for ci, (root, tones) in enumerate(CHORDS):
        t0 = base + ci*2*BEAT
        v = voicing(tones)
        rootlow = pitch(root, 2)
        if rootlow < N('D2'): rootlow += 12
        # bass (pizz + soft bass)
        add(PIZZ, t0, rootlow+12, 92, int(BEAT*0.9))
        add(BASS, t0, rootlow, 80, int(BEAT*1.8))
        if full and not last:
            add(PIZZ, t0+E*3, rootlow+12, 70, int(E*0.9))
            add(PIZZ, t0+BEAT*1.5, rootlow+19, 66, int(E*0.8))  # fifth
        # piano comp: broken chord pattern
        if intro:
            # gentle arpeggio: eighth notes up
            arp = [v[0], v[1], v[2], v[1]+12 if v[1]+12 < N('C6') else v[1]]
            for k, p in enumerate(arp): add(PIANO, t0 + k*E, p, 64, int(E*1.6))
        else:
            add(PIANO, t0, v[0], 78, int(E*0.95)); add(PIANO, t0, v[1], 74, int(E*0.95)); add(PIANO, t0, v[2], 76, int(E*0.95))
            add(PIANO, t0+E, v[0]+12 if v[0]+12 < N('D6') else v[0], 58, int(E*0.9))
            add(PIANO, t0+BEAT, v[1], 70, int(E*0.9)); add(PIANO, t0+BEAT, v[2], 72, int(E*0.9))
            add(PIANO, t0+BEAT+E, v[2]+ (0 if v[2] > N('B4') else 12), 60, int(E*0.9))
            if full: add(PIANO, t0+BEAT+E+S16, v[0], 52, int(S16*0.9))
        # pad
        if cyc >= 1:
            for p in v: add(PAD, t0, p, 42 if not last else 50, int(BEAT*2*0.98))
        # drums (channel 9)
        if full and not last:
            for b in range(2):
                tb = t0 + b*BEAT
                add(9, tb, 42, 66 if b == 0 else 58, S16)          # closed hat on beats
                add(9, tb+E, 42, 50, S16)                           # hat offbeat
                add(9, tb+S16, 70, 34, S16); add(9, tb+E+S16, 70, 46, S16)  # shaker 16ths
            beat_in_bar = (ci % 2)*2  # chords 2 beats; bar = 2 chords
            if beat_in_bar == 0:
                add(9, t0, 36, 100, S16)                 # kick beat 1
                add(9, t0+BEAT, 37 if cyc < 4 else 38, 84, S16)  # side-stick / snare beat 2
                if cyc >= 4: add(9, t0+BEAT+E, 36, 70, S16)      # kick 'and of 2'
            else:
                add(9, t0, 36, 92, S16)                  # kick beat 3
                add(9, t0+BEAT, 37 if cyc < 4 else 38, 88, S16)  # beat 4
                if cyc >= 4: add(9, t0+BEAT, 54, 48, S16)        # tambourine
                if ci == 7: add(9, t0+BEAT+E, 46, 60, E)         # open hat end of cycle
        if cyc == 1:
            for b in range(2):
                add(9, t0+b*BEAT, 42, 52, S16); add(9, t0+b*BEAT+E, 42, 40, S16)
            if ci % 2 == 0: add(9, t0, 36, 80, S16)
            else: add(9, t0+BEAT, 37, 70, S16)
    # melodies
    if cyc == 0:
        play_line(GLOCK, cyc, lineA, 70, 0.9)
    elif cyc == 1:
        play_line(EPIANO, cyc, lineA2, 84, 0.95); play_line(GLOCK, cyc, lineA2, 54, 0.9, 12)
    elif cyc == 2:
        play_line(EPIANO, cyc, lineB, 88, 0.9)
    elif cyc == 3:
        play_line(EPIANO, cyc, lineC(), 86, 0.9); play_line(GLOCK, cyc, lineA, 62, 0.9)
    elif cyc == 4:
        play_line(EPIANO, cyc, lineA, 92, 0.95); play_line(GLOCK, cyc, lineD, 66, 0.8)
    elif cyc == 5:
        play_line(EPIANO, cyc, lineA2, 92, 0.95); play_line(GLOCK, cyc, lineB, 60, 0.9, 12)
    elif cyc == 6:
        play_line(EPIANO, cyc, lineB, 90, 0.9); play_line(GLOCK, cyc, lineA, 64, 0.9, 12)
    elif cyc == 7:
        play_line(EPIANO, cyc, lineC(), 88, 0.9); play_line(GLOCK, cyc, lineA2, 66, 0.9, 12)
    else:
        play_line(EPIANO, cyc, lineA, 84, 0.98); play_line(GLOCK, cyc, lineA, 60, 0.95, 12)
# final D major hit
tend = NCYC*CYC
for ch, vel in ((PIANO, 84), (PAD, 60), (EPIANO, 80)):
    for p in (N('D3'), N('A3'), N('D4'), N('F#4'), N('A4'), N('D5')): add(ch, tend, p, vel, 4*BEAT)
add(GLOCK, tend, N('D6'), 70, 4*BEAT); add(GLOCK, tend+E, N('A6'), 60, 3*BEAT); add(GLOCK, tend+BEAT, N('F#6'), 56, 3*BEAT)
add(PIZZ, tend, N('D3'), 90, 2*BEAT); add(BASS, tend, N('D2'), 84, 4*BEAT); add(9, tend, 36, 100, S16); add(9, tend, 49, 80, 2*BEAT)
# write tracks
meta = MidiTrack(); mid.tracks.append(meta)
meta.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0))
meta.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
for ch in sorted(events):
    tr = MidiTrack(); mid.tracks.append(tr)
    if ch != 9:
        tr.append(Message('program_change', program=progs[ch], channel=ch, time=0))
    vol = {PIANO: 96, PIZZ: 90, PAD: 70, GLOCK: 72, EPIANO: 96, BASS: 84, 9: 82}[ch]
    tr.append(Message('control_change', control=7, value=vol, channel=ch, time=0))
    tr.append(Message('control_change', control=91, value=60 if ch != 9 else 30, channel=ch, time=0))  # reverb
    tr.append(Message('control_change', control=10, value={PIANO: 54, PIZZ: 74, PAD: 64, GLOCK: 80, EPIANO: 50, BASS: 64, 9: 64}[ch], channel=ch, time=0))
    evs = sorted(events[ch], key=lambda e: (e[0], 0 if e[1].type == 'note_off' else 1))
    t = 0
    for tick, msg in evs:
        msg.time = tick - t; t = tick; tr.append(msg)
mid.save(OUT)
print('saved', OUT, 'length(s)=', round(mid.length, 1))
