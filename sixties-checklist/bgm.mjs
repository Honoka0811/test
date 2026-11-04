// BGM: ヴィヴァルディ「四季」より「春」第1楽章の冒頭テーマ(パブリックドメイン)を
// 明るいポップ・クラシック風に編曲し、GeneralUser GS SoundFont で演奏して WAV に書き出す。
// 使い方: node bgm.mjs [秒数] [出力wav]
import { SpessaSynthProcessor, SpessaSynthSequencer, SoundBankLoader, MIDIBuilder, DefaultGSReverb, DefaultGSChorus } from 'spessasynth_core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TOTAL = parseFloat(process.argv[2] || '66.6');
const OUT = process.argv[3] || path.join(HERE, 'output', 'bgm.wav');
const SF2 = path.join(HERE, 'node_modules', 'generaluser', 'GeneralUser.sf2');

const SR = 48000, BPM = 119, PPQ = 480;
const Q = PPQ, E = PPQ / 2, S = PPQ / 4, BAR = PPQ * 4;
const secPerTick = 60 / BPM / PPQ;

// ---------- チャンネル / 音色(GM) ----------
const CH = { mel: 0, piano: 1, bass: 2, pad: 3, pizz: 4, glock: 5, mel2: 6, drums: 9 };
const PROG = { [CH.mel]: 48, [CH.piano]: 0, [CH.bass]: 33, [CH.pad]: 49, [CH.pizz]: 45, [CH.glock]: 9, [CH.mel2]: 40 };
const VOL = { [CH.mel]: 112, [CH.piano]: 96, [CH.bass]: 100, [CH.pad]: 58, [CH.pizz]: 104, [CH.glock]: 78, [CH.mel2]: 84, [CH.drums]: 104 };
const PAN = { [CH.mel]: 60, [CH.piano]: 44, [CH.bass]: 64, [CH.pad]: 64, [CH.pizz]: 84, [CH.glock]: 80, [CH.mel2]: 70, [CH.drums]: 64 };
const D = { kick: 36, snare: 38, clap: 39, rim: 37, hh: 42, hho: 46, crash: 49, ride: 51, tamb: 54, shaker: 82 };

let seed = 11;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const hum = (v, r = 6) => Math.max(1, Math.min(127, Math.round(v + (rnd() - 0.5) * 2 * r)));

const m = new MIDIBuilder({ timeDivision: PPQ, initialTempo: BPM, format: 0, name: 'Spring (pop arrangement)' });
const events = [];
function note(ch, tick, dur, pitch, vel, jitter = 4) {
  const t = Math.max(0, Math.round(tick + (rnd() - 0.5) * 2 * jitter));
  events.push([t, ch, pitch, hum(vel), Math.max(S / 2, dur - 10)]);
}
function chordNotes(ch, tick, dur, pitches, vel, strum = 0) {
  pitches.forEach((p, i) => note(ch, tick + i * strum, dur, p, vel));
}

// ---------- 和声 ----------
const KEY = [4, 6, 8, 9, 11, 1, 3];            // E メジャースケール(ピッチクラス)
const CHORD = {
  E: { root: 40, tri: [64, 68, 71], pad: [52, 59, 64, 68] },
  B: { root: 47, tri: [63, 66, 71], pad: [47, 59, 63, 66] },
  B7: { root: 47, tri: [63, 66, 69, 71], pad: [47, 59, 63, 69] },
  Cm: { root: 49, tri: [61, 64, 68], pad: [49, 56, 61, 64] },
  A: { root: 45, tri: [61, 64, 69], pad: [45, 57, 61, 64] },
  Fm: { root: 42, tri: [61, 66, 69], pad: [42, 54, 61, 66] },
};
const inKey = p => KEY.includes(((p % 12) + 12) % 12);
function scaleDown(from, n) { const out = []; let p = from; while (out.length < n) { if (inKey(p)) out.push(p); p--; } return out; }
function scaleUp(from, n) { const out = []; let p = from; while (out.length < n) { if (inKey(p)) out.push(p); p++; } return out; }

// ---------- パート生成 ----------
function drums(bar, style) {
  const t = bar * BAR;
  if (style === 'off') return;
  if (style === 'light') {
    note(CH.drums, t, E, D.kick, 100, 0);
    note(CH.drums, t + 2 * Q, E, D.rim, 70, 0);
    for (let i = 0; i < 8; i++) note(CH.drums, t + i * E, S, D.hh, i % 2 ? 50 : 68, 2);
    return;
  }
  // full / echo
  const acc = style === 'full';
  note(CH.drums, t, E, D.kick, 112, 0);
  note(CH.drums, t + 1.5 * Q, E, D.kick, 92, 0);
  note(CH.drums, t + 2 * Q, E, D.kick, 106, 0);
  note(CH.drums, t + Q, E, D.snare, acc ? 104 : 84, 0);
  note(CH.drums, t + 3 * Q, E, D.snare, acc ? 108 : 88, 0);
  if (acc) { note(CH.drums, t + Q, E, D.clap, 86, 0); note(CH.drums, t + 3 * Q, E, D.clap, 90, 0); }
  for (let i = 0; i < 8; i++) {
    const open = (i === 7 && bar % 2 === 1);
    note(CH.drums, t + i * E, S, open ? D.hho : D.hh, i % 2 ? 56 : 80, 2);
  }
  if (acc) for (let i = 0; i < 16; i++) note(CH.drums, t + i * S, S / 2, D.shaker, i % 4 === 2 ? 72 : 46, 3);
  if (style === 'full' && bar % 2 === 1) { note(CH.drums, t + 3.5 * Q, S, D.snare, 70, 0); note(CH.drums, t + 3.75 * Q, S, D.snare, 80, 0); }
}
function fill(bar) {  // 小節後半のスネア・ロール(次のセクションへ)
  const t = bar * BAR + 2 * Q;
  for (let i = 0; i < 8; i++) note(CH.drums, t + i * S, S, D.snare, 60 + i * 7, 0);
  note(CH.drums, t + 2 * Q - S, S, D.kick, 100, 0);
}
function crash(bar) { note(CH.drums, bar * BAR, Q, D.crash, 110, 0); }

function bass(bar, chords, style = 'pop') {  // chords: [名前 × 2](前半/後半)
  const t = bar * BAR;
  chords.forEach((c, h) => {
    const r = CHORD[c].root; const t0 = t + h * 2 * Q;
    if (style === 'pad') { note(CH.bass, t0, 2 * Q, r, 96); return; }
    // 8 分: ルート・ルート・オクターブ・ルート(ポップ)
    const pat = [[0, r, 104], [E, r, 82], [Q, r + 12, 92], [Q + E, r, 80]];
    pat.forEach(([o, p, v]) => note(CH.bass, t0 + o, E, p, v, 3));
  });
}
function pianoComp(bar, chords, style = 'pop') {
  const t = bar * BAR;
  chords.forEach((c, h) => {
    const tri = CHORD[c].tri; const t0 = t + h * 2 * Q;
    if (style === 'arp') {
      const seq = [...tri, tri[0] + 12, tri[1] + 12, tri[0] + 12, tri[2], tri[1]];
      seq.slice(0, 4).forEach((p, i) => note(CH.piano, t0 + i * E, E, p, 74 + (i === 0 ? 10 : 0)));
      return;
    }
    chordNotes(CH.piano, t0, E, tri, 86, 6);
    chordNotes(CH.piano, t0 + Q + E, E, tri, 74, 6);
    if (h === 1) chordNotes(CH.piano, t0 + 3 * E, E, tri.map(p => p + 12), 66, 4);
  });
}
function pad(bar, chords, vel = 72) {
  const t = bar * BAR;
  chords.forEach((c, h) => chordNotes(CH.pad, t + h * 2 * Q, 2 * Q + E, CHORD[c].pad, vel, 0));
}

// 「春」冒頭テーマ(3 小節)。[開始ティック, 長さ, 音高]
const THEME = [
  // 1 小節目: ミ ソ# ソ# ソ# ファ#ミ シー
  [0, E, 76], [E, E, 80], [2 * E, E, 80], [3 * E, E, 80], [4 * E, S, 78], [4 * E + S, S, 76], [5 * E, 3 * E, 83],
  // 2 小節目: シシラソ# ソ# ファ#ミ シーー
  [BAR, S, 83], [BAR + S, S, 83], [BAR + 2 * S, S, 81], [BAR + 3 * S, S, 80], [BAR + 2 * E, E, 80], [BAR + 3 * E, S, 78], [BAR + 3 * E + S, S, 76], [BAR + 4 * E, 4 * E, 83],
  // 3 小節目: シシラソ# ラ シーー
  [2 * BAR, S, 83], [2 * BAR + S, S, 83], [2 * BAR + 2 * S, S, 81], [2 * BAR + 3 * S, S, 80], [2 * BAR + 2 * E, E, 81], [2 * BAR + 3 * E, 5 * E, 83],
];
const THEME_CHORDS = [['E', 'E'], ['E', 'B'], ['B', 'E']];
function theme(bar, { ch = CH.mel, vel = 100, octave = 0, glock = false, double = false } = {}) {
  const t = bar * BAR;
  THEME.forEach(([o, d, p]) => {
    note(ch, t + o, d, p + octave, vel);
    if (double) note(CH.mel2, t + o, d, p + octave, vel - 14);
    if (glock) note(CH.glock, t + o, Math.min(d, Q), p + 12, 84);
  });
}
// 中間部: 16 分音符のアルペジオ+下行スケール(ヴィヴァルディ風の連続)
function run(bar, c, vel = 96) {
  const t = bar * BAR; const tri = CHORD[c].tri;
  const up = [tri[0] + 12, tri[1] + 12, tri[2] + 12, tri[0] + 24];
  const seq = [...up, ...up.map(p => p), ...scaleDown(tri[0] + 23, 8)];
  seq.forEach((p, i) => { note(CH.mel, t + i * S, S, p, vel - (i % 4 === 0 ? 0 : 12)); if (i % 2 === 0) note(CH.piano, t + i * S, S, p - 12, 70); });
}

// ---------- 構成(1 小節 ≈ 2.02 秒) ----------
let bar = 0;
// イントロ 2 小節: ビートとベースで引き込む
for (let i = 0; i < 2; i++) {
  drums(bar + i, i === 0 ? 'light' : 'echo');
  bass(bar + i, ['E', 'E']);
  pianoComp(bar + i, ['E', 'E']);
  pad(bar + i, ['E', 'E'], 60);
}
// グロッケンでテーマの予告
[[0, 76], [E, 80], [2 * E, 80], [3 * E, 80], [4 * E, 78], [4 * E + S, 76], [5 * E, 83]].forEach(([o, p]) => note(CH.glock, BAR + o, E, p + 12, 80));
fill(1); bar = 2;

function sectionA(bar, { full = true, glock = false } = {}) {
  crash(bar);
  theme(bar, { vel: full ? 104 : 96, glock, double: true });
  for (let i = 0; i < 3; i++) { drums(bar + i, 'full'); bass(bar + i, THEME_CHORDS[i]); pianoComp(bar + i, THEME_CHORDS[i]); pad(bar + i, THEME_CHORDS[i], 74); }
  // エコー(弱く・ピチカート+グロッケン)
  theme(bar + 3, { ch: CH.pizz, vel: 100, glock: true });
  for (let i = 0; i < 3; i++) { drums(bar + 3 + i, 'echo'); bass(bar + 3 + i, THEME_CHORDS[i]); pianoComp(bar + 3 + i, THEME_CHORDS[i], 'arp'); pad(bar + 3 + i, THEME_CHORDS[i], 64); }
  fill(bar + 5);
  return bar + 6;
}
function sectionB(bar) {
  crash(bar);
  const prog = ['Cm', 'A', 'E', 'B', 'Cm', 'A', 'B', 'B'];
  prog.forEach((c, i) => {
    const b = bar + i;
    drums(b, 'full'); bass(b, [c, c]); pad(b, [c, c], 70);
    if (i < 7) run(b, c, 98);
    else { // 最後の小節: シ を 8 分で刻んでテーマへ
      for (let k = 0; k < 8; k++) { note(CH.mel, b * BAR + k * E, E, 83, 90 + k * 3); note(CH.mel2, b * BAR + k * E, E, 71, 80); }
      chordNotes(CH.piano, b * BAR, Q, CHORD.B7.tri, 90, 8); chordNotes(CH.piano, b * BAR + 2 * Q, Q, CHORD.B7.tri.map(p => p + 12), 96, 8);
      fill(b);
    }
  });
  return bar + 8;
}
function bridge(bar) {
  const prog = ['A', 'B', 'Cm', 'B7'];
  const melody = [[73, 4 * Q], [75, 4 * Q], [76, 2 * Q], [80, 2 * Q], [78, 4 * Q]];
  let mi = 0, mt = bar * BAR;
  melody.forEach(([p, d]) => { note(CH.mel, mt, d, p, 92); note(CH.mel2, mt, d, p - 12, 80); mt += d; });
  prog.forEach((c, i) => {
    const b = bar + i;
    drums(b, 'light'); bass(b, [c, c], 'pad'); pianoComp(b, [c, c], 'arp'); pad(b, [c, c], 78);
    if (i === 3) { fill(b); for (let k = 0; k < 8; k++) note(CH.glock, b * BAR + k * E, E, scaleUp(76, 8)[k], 70 + k * 4); }
  });
  return bar + 4;
}

bar = sectionA(bar);                  // 2–7
bar = sectionB(bar);                  // 8–15
bar = sectionA(bar, { glock: true }); // 16–21
bar = bridge(bar);                    // 22–25
bar = sectionA(bar, { glock: true }); // 26–31
// 終止: E の和音を伸ばす
crash(bar);
chordNotes(CH.mel, bar * BAR, 2 * BAR, [76, 80, 83, 88], 100, 0);
chordNotes(CH.pad, bar * BAR, 2 * BAR, CHORD.E.pad, 84, 0);
chordNotes(CH.piano, bar * BAR, 2 * BAR, [52, 59, 64, 68, 71, 76], 100, 12);
note(CH.bass, bar * BAR, 2 * BAR, 40, 104);
note(CH.drums, bar * BAR, Q, D.kick, 110, 0);
[88, 83, 80, 76].forEach((p, i) => note(CH.glock, bar * BAR + Q + i * E, Q, p, 80));
const LAST_TICK = (bar + 2) * BAR;

// ---------- MIDI 化 ----------
for (const [ch, p] of Object.entries(PROG)) m.programChange(0, 0, +ch, p);
for (const ch of Object.values(CH)) {
  m.controllerChange(0, 0, ch, 7, VOL[ch]);
  m.controllerChange(0, 0, ch, 10, PAN[ch]);
  m.controllerChange(0, 0, ch, 91, ch === CH.drums ? 28 : (ch === CH.bass ? 10 : 58));
  m.controllerChange(0, 0, ch, 93, ch === CH.pad || ch === CH.piano ? 24 : 0);
}
events.sort((a, b) => a[0] - b[0]);
for (const [t, ch, p, v, d] of events) { m.noteOn(t, 0, ch, p, v); m.noteOff(t + d, 0, ch, p); }
m.noteOn(LAST_TICK, 0, CH.pad, 52, 1); m.noteOff(LAST_TICK + 1, 0, CH.pad, 52);
m.flush();
fs.mkdirSync(path.dirname(OUT), { recursive: true });
try { fs.writeFileSync(OUT.replace(/\.wav$/, '.mid'), Buffer.from(m.writeMIDI())); } catch (e) { /* 書けなくても続行 */ }
console.log(`bars=${bar + 2}  music=${(LAST_TICK * secPerTick).toFixed(1)}s  target=${TOTAL}s  notes=${events.length}`);

// ---------- レンダリング ----------
const sf = fs.readFileSync(SF2);
const synth = new SpessaSynthProcessor(SR, { effectsEnabled: true, gsReverbProcessor: new DefaultGSReverb(SR, 128), gsChorusProcessor: new DefaultGSChorus(SR, 128) });
synth.soundBankManager.addSoundBank(SoundBankLoader.fromArrayBuffer(sf.buffer.slice(sf.byteOffset, sf.byteOffset + sf.byteLength)), 'main');
await synth.ready;
const seq = new SpessaSynthSequencer(synth);
seq.loadNewSongList([m]); seq.play();
const total = Math.ceil(TOTAL * SR), BUF = 128;
const L = new Float32Array(total), R = new Float32Array(total);
for (let i = 0; i < total; i += BUF) {
  seq.processTick();
  const n = Math.min(BUF, total - i);
  const l = new Float32Array(n), r = new Float32Array(n);
  synth.process(l, r);
  L.set(l, i); R.set(r, i);
}
// 末尾 2.5 秒フェードアウト、ピーク正規化
const fo = Math.floor(2.5 * SR);
for (let i = 0; i < fo; i++) { const g = Math.pow(1 - i / fo, 1.3); L[total - fo + i] *= g; R[total - fo + i] *= g; }
let peak = 0; for (let i = 0; i < total; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
const g = 0.9 / (peak || 1);
const out = Buffer.alloc(44 + total * 4);
out.write('RIFF', 0); out.writeUInt32LE(36 + total * 4, 4); out.write('WAVEfmt ', 8); out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22);
out.writeUInt32LE(SR, 24); out.writeUInt32LE(SR * 4, 28); out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34); out.write('data', 36); out.writeUInt32LE(total * 4, 40);
for (let i = 0; i < total; i++) {
  out.writeInt16LE(Math.round(Math.max(-1, Math.min(1, L[i] * g)) * 32767), 44 + i * 4);
  out.writeInt16LE(Math.round(Math.max(-1, Math.min(1, R[i] * g)) * 32767), 46 + i * 4);
}
fs.writeFileSync(OUT, out);
console.log('wrote', OUT, `${(total / SR).toFixed(1)}s  peak=${peak.toFixed(3)}`);
