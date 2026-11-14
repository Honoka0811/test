// シーン構成とメイン描画。時刻はすべて build/timeline.js(ナレーション実測)から決まる。
const TL = window.TIMELINE;
const PLAN = buildPlan(TL), S = PLAN.S;
window.FPS = TL.fps || 60;
window.DURATION = TL.duration;
window.PLAN = PLAN;
window.READY = Promise.all([
  document.fonts.load('900 40px "Noto Sans JP"', 'あ漢1'), document.fonts.load('700 40px "Noto Sans JP"', 'あ漢1'),
  document.fonts.load('500 40px "Noto Sans JP"', 'あ漢1'),
  document.fonts.load('400 40px "Anton"', '0123'), document.fonts.load('700 40px "Oswald"', 'km'), Globe.load(),
]).then(() => document.fonts.ready);

const T_END = TL.duration;
const COL_SPIN = C.cyan, COL_ORB = C.orange, COL_GAL = C.yellow;
const STAGE_CY = 830;

const SPEED_KEYS = [[0, 1050], [S.promise, 1050], [S.spin - 0.2, 600], [S.spin + 0.5, 150], [S.orbit - 0.2, 150], [S.orbit + 0.5, 430],
  [S.galaxy - 0.3, 430], [S.galaxy + 0.5, 1500], [S.payoff, 1500], [S.payoff + 0.25, 2600], [T_END, 1050]];

// 画面を揺らす・光らせるタイミング
const HITS = [[S.hit500, 1], [S.spinLane + 0.45, 0.55], [S.orbitLane + 0.45, 0.55], [S.galaxyWord, 0.9], [S.match, 0.8],
  [S.parkerWin, 0.6], [S.lapYears, 0.7], [S.humanFrac, 0.5], [S.payoff, 1.4]].filter(h => isFinite(h[0]));
function shakeAt(t) {
  let x = 0, y = 0;
  for (const [t0, a] of HITS) {
    const d = t - t0; if (d < 0 || d > 0.5) continue;
    const k = a * 16 * Math.exp(-d / 0.09);
    x += k * Math.sin(d * 95 + t0); y += k * Math.cos(d * 83 + t0 * 2);
  }
  return [x, y];
}
function flashAt(t) {
  let f = 0;
  for (const [t0, a] of HITS) { const d = t - t0; if (d >= 0 && d < 0.35) f = Math.max(f, a * 0.42 * Math.pow(1 - d / 0.35, 2)); }
  return f;
}
const pulseAt = (t, t0, dur = 0.35) => { const d = t - t0; return d < 0 || d > dur ? 0 : Math.pow(1 - d / dur, 2); };

// ---------------------------------------------------------------- 小物
function chip(x, y, badge, title, color, alpha = 1, k = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x - 40 * (1 - k), y);
  const bw = measure(badge, 30, F.jp, 900) + 36;
  bar(0, -40, bw, 52, 26, color);
  text(badge, bw / 2, -3, { size: 30, color: '#06102e', align: 'center', weight: 900 });
  text(title, bw + 18, 2, { size: 52, color: C.ink, weight: 900, stroke: 'rgba(3,6,26,0.85)', sw: 10 });
  ctx.restore();
}
// 「時速 1,360 km」のような大きい数字。x は左端、y はベースライン
function bigNum(x, y, pre, num, unit, color, o = {}) {
  const { size = 140, alpha = 1, pop = 1, align = 'left', preSize = 44, sub = '', subColor = C.ink3 } = o;
  if (alpha <= 0) return;
  const wPre = pre ? measure(pre, preSize, F.jp, 900) + 12 : 0, wNum = measure(num, size, F.num, 400), wUnit = unit ? measure(unit, size * 0.4, F.num, 400) + 10 : 0;
  const total = wPre + wNum + wUnit;
  let x0 = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.translate(x0 + total / 2, y - size * 0.35); ctx.scale(pop, pop); ctx.translate(-(x0 + total / 2), -(y - size * 0.35));
  if (pre) text(pre, x0, y, { size: preSize, color: C.ink, stroke: 'rgba(3,6,26,0.9)', sw: 10 });
  text(num, x0 + wPre, y, { size, family: F.num, weight: 400, color, stroke: 'rgba(3,6,26,0.9)', sw: size * 0.09, glow: color, glowBlur: 26 });
  if (unit) text(unit, x0 + wPre + wNum + 10, y, { size: size * 0.4, family: F.num, weight: 400, color, stroke: 'rgba(3,6,26,0.9)', sw: 8 });
  if (sub) text(sub, x0, y + 40, { size: 27, color: subColor, weight: 700, stroke: 'rgba(3,6,26,0.9)', sw: 6 });
  ctx.restore();
}
function pillLabel(cx, cy, str, o = {}) {
  const { size = 36, color = C.ink, fill = 'rgba(8,16,52,0.86)', line = C.cyan, alpha = 1, k = 1, icon = true } = o;
  if (alpha <= 0) return;
  const w = measure(str, size, F.jp, 900) + size * 1.5 + (icon ? size * 0.9 : 0), h = size * 1.75;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(cx, cy + (1 - k) * 26); ctx.scale(0.9 + 0.1 * k, 0.9 + 0.1 * k);
  rr(-w / 2, -h / 2, w, h, h / 2); ctx.fillStyle = fill; ctx.fill(); ctx.strokeStyle = line; ctx.lineWidth = 3; ctx.stroke();
  let x = -w / 2 + size * 0.75;
  if (icon) { markCheck(x + size * 0.32, 0, size * 0.34, line, size * 0.16); x += size * 0.9; }
  text(str, x, size * 0.36, { size, color, weight: 900 });
  ctx.restore();
}
function countStr(target, t, t0, dur = 0.45) { return fmtInt(Math.round(target * ease.out(seg(t, t0, dur)))); }
function arcArrow(cx, cy, r, a0, a1, color, lw = 6, alpha = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1, a1 < a0); ctx.stroke();
  const dir = a1 < a0 ? -1 : 1, x = cx + Math.cos(a1) * r, y = cy + Math.sin(a1) * r, ta = a1 + dir * Math.PI / 2;
  ctx.translate(x, y); ctx.rotate(ta); ctx.beginPath(); ctx.moveTo(lw * 2.6, 0); ctx.lineTo(-lw * 1.2, -lw * 2); ctx.lineTo(-lw * 1.2, lw * 2); ctx.closePath(); ctx.fill();
  ctx.restore();
}

// ---------------------------------------------------------------- ヘッダー(メーターとゴール)
function headerState(t) {
  const toHeader = ease.inOut(seg(t, S.promise - 0.12, 0.7));
  const toHero = isFinite(S.loop) ? ease.inOut(seg(t, S.loop - 0.02, 0.62)) : 0;
  return clamp(1 - toHeader + toHero);   // 1 = 画面中央の大きいメーター、0 = 上部ヘッダー
}
function drawHeader(t) {
  const h = headerState(t);
  const heroSize = t < 30 ? 340 : 232;       // ループ直前(5 桁)は幅に収まる大きさで戻す
  const cx = 540, cy = lerp(480, 640, h), size = lerp(160, heroSize, h);
  const pz = pulseAt(t, S.hit500, 0.4) + pulseAt(t, S.match, 0.5) + pulseAt(t, S.payoff, 0.6);
  const box = drawOdometer(t, cx, cy, size * (1 + 0.05 * pz), { pulse: clamp(pz) });
  // ヒーロー時のラベル
  const aHero = clamp((h - 0.6) / 0.4);
  if (aHero > 0) {
    text('この動画が始まってから', 540, 330, { size: 42, color: C.ink2, align: 'center', weight: 700, alpha: aHero });
    text('あなたの移動距離', 540, 414, { size: 72, color: C.ink, align: 'center', alpha: aHero, stroke: 'rgba(3,6,26,0.8)', sw: 10 });
  }
  // ヘッダー時: 左に名前、右に「何に対する速さか」
  const aHead = clamp((0.4 - h) / 0.4);
  if (aHead > 0) {
    text('あなたの', box.left - 14, cy - 8, { size: 29, color: C.ink2, align: 'right', weight: 900, alpha: aHead });
    text('移動距離', box.left - 14, cy + 32, { size: 29, color: C.ink2, align: 'right', weight: 900, alpha: aHead });
    const known = seg(t, S.galaxySpeed, 0.4);
    if (known < 1) {
      text('何に対して？', box.right + 14, cy - 8, { size: 25, color: C.ink3, weight: 700, alpha: aHead * (1 - known) });
      text('→ このあと', box.right + 14, cy + 30, { size: 25, color: C.ink3, weight: 700, alpha: aHead * (1 - known) });
    }
    if (known > 0) {
      text('銀河の中心', box.right + 14, cy - 8, { size: 26, color: C.yellow, weight: 900, alpha: aHead * known });
      text('に対して', box.right + 14, cy + 30, { size: 26, color: C.yellow, weight: 900, alpha: aHead * known });
    }
    // ゴールゲージ
    const gk = ease.out(seg(t, S.promise + 0.25, 0.5));
    const done = t >= S.payoff;
    const near = seg(t, S.payoff - 7, 7);
    const pulse = done ? pulseAt(t, S.payoff, 0.8) : near * (0.5 + 0.5 * Math.sin(t * (6 + 10 * near)));
    ctx.save(); ctx.translate(0, -70 * (1 - gk));
    drawGauge(t, 328, {
      alpha: aHead * gk, goal: done ? '地球 1個ぶん' : '？？？ 1個ぶん', goalColor: done ? C.yellow : C.ink,
      pulse, ticks: PLAN.milestones.filter(m => !m.big),
    });
    ctx.restore();
  }
  return { h, box };
}

// ---------------------------------------------------------------- フック(0 秒〜)
// 画面下の地球と、日本に立つ「あなた」。冒頭とループ直前に出る(最終フレームが 0 秒の構図に戻る)。
function drawDome(t) {
  const out = ease.inOut(seg(t, S.promise + 0.1, 1.0)), back = isFinite(S.loop) ? ease.inOut(seg(t, S.loop, 0.6)) : 0;
  const k = clamp(1 - out + back);
  if (k <= 0) return;
  const p = drawEarthDome(1, (1 - k) * 520);
  if (!p) return;
  const ph = (t * 1.1) % 1, a = k;
  ring(p.x, p.y, 12 + 44 * ph, C.red, 3, a * (1 - ph));
  ring(p.x, p.y, 12 + 44 * ((ph + 0.5) % 1), C.red, 3, a * (1 - (ph + 0.5) % 1));
  pin(p.x, p.y, 30, C.red, a);
  const lx = p.x + 44, ly = p.y - 58;
  text('あなた', lx, ly, { size: 54, color: C.ink, alpha: a, stroke: 'rgba(3,6,26,0.9)', sw: 11 });
  const bx = lx + measure('あなた', 54) + 16;
  ctx.save(); ctx.globalAlpha *= a;
  rr(bx, ly - 44, 146, 54, 27); ctx.fillStyle = 'rgba(3,6,26,0.8)'; ctx.fill(); ctx.strokeStyle = C.cyan; ctx.lineWidth = 3; ctx.stroke();
  text('静止中', bx + 73, ly - 6, { size: 31, color: C.cyan, align: 'center', weight: 900 });
  ctx.restore();
}
function sceneHook(t, h) {
  const a = clamp((h - 0.55) / 0.45);
  if (a <= 0) return;
  const m0 = PLAN.milestones[0], passed = t >= m0.t && t < S.promise + 1;
  // 「何に対して?」の注記 → 最初の通過点に入れ替わる
  const tagA = a * (1 - seg(t, m0.t - 0.1, 0.15)) * (t < 30 ? 1 : 0);
  text('※「何に対して？」の答えは このあと', 540, 936, { size: 34, color: C.ink3, align: 'center', weight: 700, alpha: tagA });
  if (passed) {
    const k = ease.back(seg(t, m0.t, 0.22));
    pillLabel(540, 928, `${m0.label} 約${fmtInt(m0.km)}km 通過`, { size: 50, alpha: a * seg(t, m0.t, 0.08), k, line: C.cyan });
  }
}

// ---------------------------------------------------------------- 容疑者カード
function suspectIcon(kind, x, y, tt) {
  if (kind === 0) {           // 自転
    circle(x, y, 52, grad(x - 52, y - 52, x + 52, y + 52, [[0, '#2f8bff'], [1, '#0b2f8a']]));
    ctx.save(); ctx.strokeStyle = 'rgba(255,255,255,0.45)'; ctx.lineWidth = 2.5;
    for (const k of [0.35, 0.8]) { ctx.beginPath(); ctx.ellipse(x, y, 52 * k, 52, 0, 0, 6.2832); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(x - 52, y); ctx.lineTo(x + 52, y); ctx.stroke(); ctx.restore();
    arcArrow(x, y, 72, Math.PI * 1.15 + tt, Math.PI * 1.85 + tt, COL_SPIN, 6);
  } else if (kind === 1) {    // 公転
    circle(x, y, 24, '#FFD35A', 1, '#FFB000', 30);
    ctx.save(); ctx.strokeStyle = 'rgba(255,255,255,0.5)'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.ellipse(x, y, 82, 34, 0, 0, 6.2832); ctx.stroke(); ctx.restore();
    const a = tt * 1.6; circle(x + Math.cos(a) * 82, y + Math.sin(a) * 34, 12, '#3f9bff', 1, '#3f9bff', 14);
  } else {
    text('？', x, y + 44, { size: 124, family: F.jp, color: COL_GAL, align: 'center', glow: COL_GAL, glowBlur: 30 });
  }
}
function sceneSuspects(t) {
  const t0 = S.suspects, a = inOut(t, S.promise + 0.3, S.spin + 0.05, 0.3, 0.25);
  if (a <= 0) return;
  text('動かしている', 540, 640, { size: 44, color: C.ink2, align: 'center', weight: 900, alpha: a * seg(t, S.promise + 0.5, 0.3) });
  text('犯人はだれ？', 540, 716, { size: 70, color: C.ink, align: 'center', alpha: a * seg(t, S.promise + 0.5, 0.3), stroke: 'rgba(3,6,26,0.85)', sw: 10 });
  const names = ['自転', '公転', '？？？'], subs = ['地球が回る', '太陽を回る', '………'], cols = [COL_SPIN, COL_ORB, COL_GAL];
  for (let i = 0; i < 3; i++) {
    const k = ease.back(seg(t, t0 + i * 0.22, 0.32)), ka = seg(t, t0 + i * 0.22, 0.12);
    if (ka <= 0) continue;
    const x = 70 + i * 320, y = 760, w = 300, hh = 320;
    ctx.save(); ctx.globalAlpha *= a * ka; ctx.translate(x + w / 2, y + hh / 2); ctx.scale(0.8 + 0.2 * k, 0.8 + 0.2 * k); ctx.translate(-w / 2, -hh / 2);
    panel(0, 0, w, hh, 28, 1, C.panel, cols[i], 3);
    bar(w / 2 - 78, 18, 156, 44, 22, cols[i]);
    text('容疑者 ' + (i + 1), w / 2, 51, { size: 28, color: '#06102e', align: 'center' });
    suspectIcon(i, w / 2, 150, t - t0);
    text(names[i], w / 2, 268, { size: 56, color: C.ink, align: 'center' });
    text(subs[i], w / 2, 304, { size: 26, color: C.ink2, align: 'center', weight: 700 });
    ctx.restore();
  }
}

// ---------------------------------------------------------------- 容疑者1: 自転
function sceneSpin(t) {
  const a = inOut(t, S.spin - 0.05, S.spinV + 0.1, 0.3, 0.25);
  if (a <= 0) return;
  const tt = t - S.spin, k = ease.out(seg(t, S.spin, 0.5));
  chip(70, 632, '容疑者 1', '地球の自転', COL_SPIN, a, k);
  const gx = 292, gy = 862, r = 208 * (0.85 + 0.15 * k), lon0 = 172 - tt * 8.5, lat0 = 22;
  drawGlobe(gx, gy, r, lon0, lat0, a);
  arcArrow(gx, gy, r + 26, Math.PI * 1.22, Math.PI * 1.78, COL_SPIN, 7, a * k);
  text('東へ', gx + 6, gy - r - 44, { size: 30, color: COL_SPIN, align: 'center', alpha: a * k, weight: 900 });
  const p = Globe.project(35.68, 139.77, lon0, lat0, r);
  if (p.visible) {
    const px = gx + p.x, py = gy + p.y, ph = (t * 1.4) % 1;
    ring(px, py, 10 + 30 * ph, C.red, 3, a * (1 - ph));
    circle(px, py, 9, C.red, a, C.red, 18);
    text('東京', px + 6, py - 20, { size: 34, color: C.ink, alpha: a, align: 'center', stroke: 'rgba(3,6,26,0.9)', sw: 8 });
  }
  // 右: 速さ
  const sA = a * seg(t, S.spinSpeed - 0.05, 0.12), sP = 0.8 + 0.2 * ease.back(seg(t, S.spinSpeed - 0.05, 0.3));
  text('東京の地面は', 560, 740, { size: 38, color: C.ink2, alpha: a * seg(t, S.spinSpeed - 0.5, 0.25), weight: 900 });
  bigNum(560, 880, '時速', countStr(1360, t, S.spinSpeed - 0.05, 0.4), 'km', COL_SPIN, { size: 128, alpha: sA, pop: sP, sub: '（地球の中心に対して）' });
  // 音速との比較
  const bA = a * seg(t, S.sound - 0.05, 0.2);
  if (bA > 0) {
    const x0 = 560, wMax = 340, g = ease.out(seg(t, S.sound - 0.05, 0.45));
    text('音速', x0, 990, { size: 30, color: C.ink2, alpha: bA, weight: 900 });
    bar(x0 + 100, 966, wMax * (1225 / 1360) * g, 28, 14, 'rgba(255,255,255,0.75)', bA);
    text('1,225', x0 + 100 + wMax * (1225 / 1360) * g - 10, 990, { size: 26, family: F.num, weight: 400, color: '#06102e', align: 'right', alpha: bA * seg(g, 0.6, 0.4) });
    text('東京', x0, 1038, { size: 30, color: COL_SPIN, alpha: bA, weight: 900 });
    bar(x0 + 100, 1014, wMax * g, 28, 14, COL_SPIN, bA, COL_SPIN);
    text('1,360', x0 + 100 + wMax * g - 10, 1038, { size: 26, family: F.num, weight: 400, color: '#06102e', align: 'right', alpha: bA * seg(g, 0.6, 0.4) });
  }
}

// ---------------------------------------------------------------- 判定パネル(その動きだけで進める距離 vs メーター)
const ROWS = [
  { name: '自転', v: V_SPIN, col: COL_SPIN, dec: 1 },
  { name: '公転', v: V_ORB, col: COL_ORB, dec: 0 },
  { name: '銀河', v: V_GAL, col: COL_GAL, dec: 0 },
];
function sceneVerdict(t, idx, tIn, tOut, tStamp) {
  const a = inOut(t, tIn - 0.05, tOut + 0.05, 0.25, 0.22);
  if (a <= 0) return;
  const k = ease.out(seg(t, tIn - 0.05, 0.4));
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(0, 40 * (1 - k));
  panel(50, 610, 980, 474, 30, 1);
  text('その動き「だけ」で進める距離', 86, 672, { size: 38, color: C.ink2, weight: 900 });
  const tx0 = 250, tw = 520;
  // メーター(100%)の基準線
  lineSeg(tx0 + tw, 712, tx0 + tw, 1062, 'rgba(255,225,74,0.7)', 3, 1, [8, 8]);
  text('メーター', tx0 + tw, 704, { size: 26, color: C.yellow, align: 'center', weight: 900 });
  for (let i = 0; i < 3; i++) {
    const R = ROWS[i], y = 770 + i * 108, isNew = i === idx, future = i > idx;
    if (future) {                                // まだ調べていない容疑者
      ctx.save(); ctx.globalAlpha *= 0.4;
      text(i === 2 ? '？？？' : R.name, 150, y + 16, { size: 46, color: C.ink2 });
      bar(tx0, y - 26, tw, 54, 27, 'rgba(255,255,255,0.09)');
      text('—', 1000, y + 18, { size: 50, family: F.num, weight: 400, color: C.ink3, align: 'right' });
      ctx.restore();
      continue;
    }
    const g = isNew ? ease.out(seg(t, tIn + 0.15, i === 2 ? Math.max(0.5, tStamp - tIn - 0.2) : 0.5)) : 1;
    const stamped = !isNew || t >= tStamp, sk = isNew ? ease.back(seg(t, tStamp, 0.25)) : 1;
    const jx = isNew && i < 2 ? 10 * pulseAt(t, tStamp, 0.3) * Math.sin((t - tStamp) * 90) : 0;
    ctx.save(); ctx.translate(jx, 0);
    if (isNew) { ctx.save(); ctx.globalAlpha *= 0.5 + 0.5 * Math.sin(t * 9) * (stamped ? 0 : 1); rr(70, y - 46, 940, 94, 20); ctx.strokeStyle = R.col; ctx.lineWidth = 3; ctx.stroke(); ctx.restore(); }
    text(R.name, 150, y + 16, { size: 46, color: C.ink, align: 'left' });
    bar(tx0, y - 26, tw, 54, 27, 'rgba(255,255,255,0.09)');
    const share = R.v / V_GAL;
    bar(tx0, y - 26, Math.max(i === 0 ? 7 : 12, tw * share * g), 54, i === 0 ? 3.5 : 27, R.col, 1, R.col);
    const dist = R.v * t, val = (R.dec ? dist.toFixed(1) : fmtInt(dist));
    text(val, 1000 - measure('km', 30, F.num, 400) - 8, y + 22, { size: 64, family: F.num, weight: 400, color: R.col, align: 'right' });
    text('km', 1000, y + 22, { size: 30, family: F.num, weight: 400, color: R.col, align: 'right' });
    if (stamped) {
      if (i < 2) markCross(110, y, 20 * sk, C.red, 9, 1);
      else { markCheck(108, y, 24 * sk, C.green, 10, 1); }
    }
    ctx.restore();
  }
  // 判定の言葉
  if (t >= tStamp) {
    const sk = ease.back(seg(t, tStamp, 0.25)), y = 770 + idx * 108;
    if (idx < 2) text('足りない', tx0 + tw * 0.5, y + 16, { size: 44, color: C.red, align: 'center', alpha: seg(t, tStamp, 0.1), stroke: 'rgba(3,6,26,0.95)', sw: 10, size: 44 * (0.7 + 0.3 * sk) });
    else text('ぴったり一致', tx0 + tw * 0.5, y + 16, { size: 44 * (0.7 + 0.3 * sk), color: '#06102e', align: 'center', alpha: seg(t, tStamp, 0.1) });
  }
  ctx.restore();
}

// ---------------------------------------------------------------- 容疑者2: 公転
function sceneOrbit(t) {
  const a = inOut(t, S.orbit - 0.05, S.orbitV + 0.1, 0.3, 0.25);
  if (a <= 0) return;
  const tt = t - S.orbit, k = ease.out(seg(t, S.orbit, 0.5));
  chip(70, 632, '容疑者 2', '地球の公転', COL_ORB, a, k);
  const cx = 540, cy = 880, rx = 400 * (0.8 + 0.2 * k), ry = 132 * (0.8 + 0.2 * k);
  const ang = 2.3 + tt * 0.85, ex = cx + Math.cos(ang) * rx, ey = cy + Math.sin(ang) * ry;
  const orbitHalf = (front) => {
    ctx.save(); ctx.globalAlpha *= a * 0.55; ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 3; ctx.setLineDash([4, 12]); ctx.lineCap = 'round';
    ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, front ? 0 : Math.PI, front ? Math.PI : Math.PI * 2); ctx.stroke(); ctx.restore();
  };
  const trail = () => {
    ctx.save(); ctx.lineCap = 'round';
    for (let i = 0; i < 26; i++) {
      const a0 = ang - i * 0.035, a1 = a0 - 0.035;
      ctx.globalAlpha = a * (1 - i / 26) * 0.9; ctx.strokeStyle = COL_ORB; ctx.lineWidth = 12 * (1 - i / 30);
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a0) * rx, cy + Math.sin(a0) * ry); ctx.lineTo(cx + Math.cos(a1) * rx, cy + Math.sin(a1) * ry); ctx.stroke();
    }
    ctx.restore();
  };
  const earth = () => { trail(); drawGlobe(ex, ey, 30, 140 - tt * 40, 15, a, 0.8); text('地球', ex, ey - 44, { size: 28, color: C.ink, align: 'center', alpha: a, stroke: 'rgba(3,6,26,0.9)', sw: 7 }); };
  const behind = Math.sin(ang) < 0;
  orbitHalf(false);
  if (behind) earth();
  glowBlob(cx, cy, 210, 'rgba(255,170,40,0.55)', a); glowBlob(cx, cy, 100, 'rgba(255,240,180,0.9)', a);
  circle(cx, cy, 44, rgrad(cx - 10, cy - 10, 4, 48, [[0, '#FFF8D8'], [1, '#FFB52E']]), a);
  text('太陽', cx, cy + 92, { size: 28, color: C.ink, align: 'center', alpha: a, stroke: 'rgba(3,6,26,0.9)', sw: 7 });
  orbitHalf(true);
  if (!behind) earth();
  const sA = a * seg(t, S.orbitSpeed - 0.05, 0.12), sP = 0.8 + 0.2 * ease.back(seg(t, S.orbitSpeed - 0.05, 0.3));
  bigNum(1010, 716, '秒速', countStr(30, t, S.orbitSpeed - 0.05, 0.3), 'km', COL_ORB, { size: 132, alpha: sA, pop: sP, align: 'right' });
  text('（太陽に対して）', 1010, 756, { size: 27, color: C.ink3, align: 'right', alpha: sA, weight: 700, stroke: 'rgba(3,6,26,0.9)', sw: 6 });
  if (isFinite(S.osaka)) {
    const oa = seg(t, S.osaka - 0.3, 0.12), ok = ease.back(seg(t, S.osaka - 0.3, 0.25));
    pillLabel(272, 716, '東京→大阪 13秒', { size: 40, alpha: a * oa, k: ok, line: COL_ORB, icon: false });
  }
}

// ---------------------------------------------------------------- 容疑者3: 銀河
function galaxyBackdrop(t) {
  // 銀河は判定〜探査機比較のあいだも背景として残す
  const a = inOut(t, S.galaxy - 0.05, S.lap + 0.3, 0.5, 0.5);
  if (a <= 0) return null;
  const k = ease.out5(seg(t, S.galaxy, 1.3));
  const dim = 1 - 0.62 * seg(t, S.galaxyV - 0.1, 0.4);
  const R = lerp(230, 600, k), rot = 0.5 + (t - S.galaxy) * 0.085;
  const sun = drawGalaxy(540, 850, R, rot, { alpha: a * dim, bright: 1.25 });
  return { sun, R, a, dim };
}
function sceneGalaxy(t, gb) {
  const a = inOut(t, S.galaxy - 0.05, S.galaxyV + 0.1, 0.3, 0.25);
  if (a <= 0 || !gb) return;
  const k = ease.out(seg(t, S.galaxyWord - 0.05, 0.4));
  chip(70, 632, '容疑者 3', '天の川銀河', COL_GAL, a * seg(t, S.galaxyWord - 0.05, 0.15), k);
  // 太陽系の軌道と位置
  const oa = a * seg(t, S.galaxy + 0.5, 0.5);
  ctx.save(); ctx.globalAlpha *= oa * 0.8; galaxyOrbitPath(540, 850, gb.R); ctx.strokeStyle = COL_GAL; ctx.lineWidth = 2.5; ctx.setLineDash([10, 12]); ctx.stroke(); ctx.restore();
  const [sx, sy] = gb.sun, ph = (t * 1.2) % 1;
  ring(sx, sy, 12 + 34 * ph, COL_GAL, 3, oa * (1 - ph));
  circle(sx, sy, 10, '#fff', oa, COL_GAL, 26);
  lineSeg(sx + 10, sy - 10, sx + 62, sy - 62, 'rgba(255,255,255,0.8)', 2.5, oa);
  text('太陽系', sx + 70, sy - 74, { size: 40, color: C.ink, alpha: oa, stroke: 'rgba(3,6,26,0.9)', sw: 9 });
  text('（あなたはここ）', sx + 70, sy - 38, { size: 27, color: COL_GAL, alpha: oa, weight: 900, stroke: 'rgba(3,6,26,0.9)', sw: 7 });
  text('銀河の中心', 540, 850 + 74, { size: 26, color: C.ink2, align: 'center', alpha: oa, weight: 900, stroke: 'rgba(3,6,26,0.9)', sw: 6 });
  // 速さ
  const sA = a * seg(t, S.galaxySpeed - 0.05, 0.12), sP = 0.8 + 0.2 * ease.back(seg(t, S.galaxySpeed - 0.05, 0.3));
  bigNum(1010, 720, '秒速およそ', countStr(227, t, S.galaxySpeed - 0.05, 0.4), 'km', COL_GAL, { size: 132, alpha: sA, pop: sP, preSize: 38, align: 'right' });
  text('銀河の中心に対して ／ 国立天文台 VERA（2020）', 1010, 1064, { size: 25, color: C.ink2, align: 'right', alpha: sA, weight: 700, stroke: 'rgba(3,6,26,0.9)', sw: 6 });
}

// ---------------------------------------------------------------- 人類最速の探査機との比較
function probeIcon(x, y, s, alpha) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x, y);
  ctx.fillStyle = '#e8ecff'; rr(-s * 0.9, -s * 0.28, s * 1.1, s * 0.56, 5); ctx.fill();                       // 本体
  ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.moveTo(s * 0.2, -s * 0.62); ctx.lineTo(s * 0.46, -s * 0.62); ctx.lineTo(s * 0.46, s * 0.62); ctx.lineTo(s * 0.2, s * 0.62); ctx.closePath(); ctx.fill(); // 耐熱シールド
  ctx.fillStyle = '#5aa0ff'; ctx.fillRect(-s * 0.7, -s * 0.78, s * 0.5, s * 0.42); ctx.fillRect(-s * 0.7, s * 0.36, s * 0.5, s * 0.42);   // 太陽電池
  ctx.restore();
}
function sceneParker(t) {
  if (!isFinite(S.parker)) return;
  const a = inOut(t, S.parker - 0.05, S.lap + 0.1, 0.3, 0.25);
  if (a <= 0) return;
  const k = ease.out(seg(t, S.parker, 0.4));
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(0, 30 * (1 - k));
  panel(50, 610, 980, 470, 30, 1);
  text('人類最速の探査機と くらべると', 86, 676, { size: 40, color: C.ink, weight: 900 });
  const x0 = 86, wMax = 900;
  // 探査機
  const g1 = ease.out(seg(t, S.parker + 0.15, 0.6)), w1 = wMax * (192 / 227) * g1;
  text('パーカー・ソーラー・プローブ', x0, 744, { size: 32, color: C.ink, weight: 900 });
  text('太陽に最接近したとき（太陽に対して）', x0 + 470, 744, { size: 22, color: C.ink3, weight: 700 });
  bar(x0, 760, Math.max(30, w1), 62, 16, grad(x0, 0, x0 + wMax, 0, [[0, '#1c6dff'], [1, C.cyan]]), 1, C.cyan);
  probeIcon(x0 + Math.max(30, w1) + 40, 791, 30, g1);
  text('秒速 約192km', x0 + 22, 803, { size: 36, color: '#04102e', weight: 900, alpha: seg(g1, 0.5, 0.5) });
  // あなた
  const g2 = ease.out(seg(t, S.parker + 0.55, Math.max(0.5, S.parkerWin - S.parker - 0.55))), w2 = wMax * g2;
  text('あなた（太陽系ごと）', x0, 906, { size: 32, color: COL_GAL, weight: 900 });
  text('銀河の中心に対して', x0 + 330, 906, { size: 22, color: C.ink3, weight: 700 });
  const wp = pulseAt(t, S.parkerWin, 0.4);
  bar(x0, 922, Math.max(30, w2), 62 + 6 * wp, 16, grad(x0, 0, x0 + wMax, 0, [[0, '#FF8A00'], [1, C.yellow]]), 1, C.yellow);
  text('秒速 約227km', x0 + 22, 965, { size: 36, color: '#04102e', weight: 900, alpha: seg(g2, 0.5, 0.5) });
  pin(x0 + Math.max(30, w2) + 26, 975, 22, COL_GAL, g2 * (1 - seg(g2, 0.93, 0.07)));
  text('※基準のちがう速さを そのまま並べた比較', x0, 1048, { size: 24, color: C.ink3, weight: 700 });
  ctx.restore();
}

// ---------------------------------------------------------------- 銀河 1 周の長さ(上から見た図)
function footprint(x, y, s, color, alpha) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = color; ctx.translate(x, y);
  for (const ang of [-0.5, 0, 0.5]) { ctx.save(); ctx.rotate(ang); ctx.beginPath(); ctx.ellipse(0, -s * 0.75, s * 0.2, s * 0.62, 0, 0, 6.2832); ctx.fill(); ctx.restore(); }
  ctx.beginPath(); ctx.ellipse(0, s * 0.05, s * 0.34, s * 0.3, 0, 0, 6.2832); ctx.fill();
  ctx.restore();
}
function sceneLap(t) {
  if (!isFinite(S.lap)) return;
  const a = inOut(t, S.lap - 0.05, S.goal + 0.1, 0.4, 0.3);
  if (a <= 0) return;
  const cx = 540, cy = 850, R = 400, rot = 1.1 + (t - S.lap) * 0.05;
  const k = ease.out(seg(t, S.lap, 0.6));
  const sun = drawGalaxy(cx, cy, R * (0.9 + 0.1 * k), rot, { tilt: 1, ang: 0, alpha: a * 0.62, bright: 1.0 });
  const rr0 = GALAXY.sun.r * R * (0.9 + 0.1 * k), sa = Math.atan2(sun[1] - cy, sun[0] - cx);
  ring(cx, cy, rr0, 'rgba(255,225,74,0.45)', 3, a, [6, 10]);
  // 1 周をなぞる光
  const lp = ease.inOut(seg(t, S.lap + 0.2, Math.max(1.2, S.lapYears - S.lap + 0.5)));
  ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = COL_GAL; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.shadowColor = COL_GAL; ctx.shadowBlur = 18;
  ctx.beginPath(); ctx.arc(cx, cy, rr0, sa, sa - Math.PI * 2 * lp, true); ctx.stroke(); ctx.restore();
  circle(sun[0], sun[1], 11, '#fff', a, COL_GAL, 26);
  text('太陽系', sun[0], sun[1] - 24, { size: 28, color: C.ink, align: 'center', alpha: a, stroke: 'rgba(3,6,26,0.9)', sw: 7 });
  // 1 周 = 約 2 億年
  const yA = a * seg(t, S.lapYears - 0.05, 0.12), yP = 0.8 + 0.2 * ease.back(seg(t, S.lapYears - 0.05, 0.3));
  text('銀河を1周', 70, 640, { size: 40, color: C.ink2, alpha: a * seg(t, S.lap + 0.1, 0.3), weight: 900, stroke: 'rgba(3,6,26,0.9)', sw: 8 });
  ctx.save(); ctx.globalAlpha *= yA; ctx.translate(70, 740); ctx.scale(yP, yP);
  const w0 = text('およそ', 0, 0, { size: 40, color: C.ink, stroke: 'rgba(3,6,26,0.9)', sw: 9 });
  const w1 = text('2', w0 + 12, 4, { size: 124, family: F.num, weight: 400, color: COL_GAL, stroke: 'rgba(3,6,26,0.9)', sw: 11, glow: COL_GAL });
  text('億年', w0 + w1 + 22, 0, { size: 72, color: COL_GAL, stroke: 'rgba(3,6,26,0.9)', sw: 11 });
  ctx.restore();
  // 前回ここにいたころ
  if (isFinite(S.dino)) {
    const dA = a * seg(t, S.dino + 0.1, 0.25), dk = ease.back(seg(t, S.dinoWord - 0.05, 0.3));
    text('1周前、このあたりにいたころ', 1010, 640, { size: 30, color: C.ink2, align: 'right', alpha: dA, weight: 900, stroke: 'rgba(3,6,26,0.9)', sw: 7 });
    const wA = a * seg(t, S.dinoWord - 0.05, 0.12);
    text('恐竜が現れたばかり', 1010, 700, { size: 46 * (0.8 + 0.2 * dk), color: C.green, align: 'right', alpha: wA, stroke: 'rgba(3,6,26,0.9)', sw: 10 });
    footprint(1010 - 46 * 9 - 44, 684, 26, C.green, wA);
    ring(sun[0], sun[1], 22 + 10 * Math.sin(t * 6), C.green, 4, wA);
  }
  // 人類の歴史 = 1 周の 1/700
  if (isFinite(S.human)) {
    const hA = a * seg(t, S.human + 0.05, 0.3), lx = 800, ly = 990, lr = 92;
    if (hA > 0) {
      lineSeg(sun[0], sun[1], lx - lr * 0.72, ly - lr * 0.72, 'rgba(255,255,255,0.7)', 2.5, hA);
      ctx.save(); ctx.globalAlpha *= hA;
      circle(lx, ly, lr, 'rgba(6,12,44,0.94)'); ring(lx, ly, lr, '#fff', 4, 1);
      ctx.save(); ctx.beginPath(); ctx.arc(lx, ly, lr - 3, 0, 6.2832); ctx.clip();
      // 拡大した軌道(ほぼ直線)と、そのうち人類の歴史ぶん
      ctx.strokeStyle = 'rgba(255,225,74,0.55)'; ctx.lineWidth = 12; ctx.beginPath(); ctx.arc(lx - 30, ly + 600, 610, -Math.PI * 0.62, -Math.PI * 0.38); ctx.stroke();
      const g = ease.out(seg(t, S.humanFrac - 0.05, 0.4));
      ctx.strokeStyle = C.pink; ctx.lineWidth = 12; ctx.lineCap = 'round'; ctx.shadowColor = C.pink; ctx.shadowBlur = 16;
      ctx.beginPath(); ctx.arc(lx - 30, ly + 600, 610, -Math.PI * 0.5 - 0.012 * g, -Math.PI * 0.5 + 0.012 * g); ctx.stroke();
      ctx.restore();
      text('拡大', lx, ly + lr - 16, { size: 22, color: C.ink2, align: 'center', weight: 900 });
      ctx.restore();
    }
    const fA = a * seg(t, S.humanFrac - 0.05, 0.12), fP = 0.8 + 0.2 * ease.back(seg(t, S.humanFrac - 0.05, 0.3));
    text('人類の歴史 約30万年', 70, 980, { size: 34, color: C.ink2, alpha: hA, weight: 900, stroke: 'rgba(3,6,26,0.9)', sw: 8 });
    ctx.save(); ctx.globalAlpha *= fA; ctx.translate(70, 1066); ctx.scale(fP, fP);
    const w0 = text('1周の', 0, 0, { size: 44, color: C.ink, stroke: 'rgba(3,6,26,0.9)', sw: 9 });
    text('1/700', w0 + 14, 4, { size: 104, family: F.num, weight: 400, color: C.pink, stroke: 'rgba(3,6,26,0.9)', sw: 10, glow: C.pink });
    ctx.restore();
  }
}

// ---------------------------------------------------------------- ゴール
// 正体不明の円(幅 = ゴールまでの距離)と、その下の物差し。メーターが 12,742km に届いた瞬間に地球が現れる。
function sceneGoal(t) {
  const tIn = isFinite(S.goal) ? S.goal : S.payoff - 4;
  const tOut = isFinite(S.loop) ? S.loop + 0.45 : T_END + 1;
  const a = inOut(t, tIn - 0.05, tOut, 0.35, 0.4);
  if (a <= 0) return;
  const cx = 540, cy = 822, r = 206, done = t >= S.payoff;
  const k = ease.out(seg(t, tIn, 0.5));
  const D = V_GAL * t, p = clamp(D / EARTH_D);
  ctx.save(); ctx.globalAlpha *= a;
  const x0 = cx - r, x1 = cx + r, y = cy + r + 40;
  if (!done) {
    const near = seg(t, S.payoff - 2.2, 2.2);
    ring(cx, cy, r * (0.9 + 0.1 * k) + 4 * near * Math.sin(t * 22), `rgba(255,255,255,${0.6 + 0.4 * near})`, 4 + 3 * near, 1, [10, 14]);
    circle(cx, cy, r * (0.9 + 0.1 * k) - 6, 'rgba(6,12,44,0.55)');
    text('？', cx, cy + 118, { size: 330, color: 'rgba(255,255,255,0.10)', align: 'center' });
    text('ゴールまで あと', cx, cy - 62, { size: 36, color: C.ink2, align: 'center', weight: 900 });
    const rem = fmtInt(Math.max(0, EARTH_D - D)), wn = measure(rem, 110, F.num, 400), wu = measure('km', 44, F.num, 400) + 10;
    text(rem, cx - (wn + wu) / 2, cy + 56, { size: 110, family: F.num, weight: 400, color: C.yellow, stroke: 'rgba(3,6,26,0.9)', sw: 10, glow: C.yellow });
    text('km', cx - (wn + wu) / 2 + wn + 10, cy + 56, { size: 44, family: F.num, weight: 400, color: C.yellow, stroke: 'rgba(3,6,26,0.9)', sw: 7 });
    text('この円の幅 ＝ ゴールの距離', cx, cy + 112, { size: 26, color: C.ink3, align: 'center', weight: 700 });
  } else {
    const pk = ease.elastic(seg(t, S.payoff, 0.7));
    drawGlobe(cx, cy, r * (0.82 + 0.18 * pk), 138, 26, 1, 1.3);
    const d = t - S.payoff;                        // 衝撃波と火花
    for (let i = 0; i < 3; i++) { const q = seg(d, i * 0.08, 0.7); ring(cx, cy, r + 440 * ease.out(q), '#fff', 6 * (1 - q), (1 - q) * 0.9); }
    const rnd = mulberry32(99);
    for (let i = 0; i < 46; i++) {
      const ang = rnd() * 6.2832, sp = 300 + rnd() * 620, q = seg(d, 0, 0.8 + rnd() * 0.4), rad = r + sp * ease.out(q);
      circle(cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad, 5 * (1 - q), rnd() < 0.5 ? C.yellow : '#fff', 1 - q, C.yellow, 12);
    }
  }
  // 物差し(円の幅ぶん。メーターの進みで埋まる)
  lineSeg(x0, y, x1, y, 'rgba(255,255,255,0.25)', 10);
  ctx.save(); ctx.shadowColor = C.yellow; ctx.shadowBlur = 18; lineSeg(x0, y, x0 + (x1 - x0) * p, y, C.yellow, 10); ctx.restore();
  lineSeg(x0, y - 22, x0, y + 22, '#fff', 4); lineSeg(x1, y - 22, x1, y + 22, '#fff', 4);
  if (!done) circle(x0 + (x1 - x0) * p, y, 12, '#fff', 1, '#fff', 22);
  else {
    const pk = ease.back(seg(t, S.payoff + 0.05, 0.3)), pa = seg(t, S.payoff + 0.05, 0.1);
    pillLabel(cx, y, '地球の直径 およそ12,742km', { size: 38, alpha: pa, k: pk, line: C.yellow, icon: false, fill: 'rgba(6,12,44,0.96)' });
  }
  ctx.restore();
}

// ---------------------------------------------------------------- 通過点・クレジット
function drawMilestones(t) {
  const fade = (1 - seg(t, S.payoff - 0.3, 0.3)) * seg(t, S.promise + 0.6, 0.4);
  if (fade <= 0) return;
  const passed = PLAN.milestones.filter(m => t >= m.t);
  if (!passed.length) return;
  const newest = passed[passed.length - 1], d = t - newest.t, slide = ease.out(seg(d, 0, 0.3));
  text('通過ログ', 480, 1296, { size: 24, color: C.ink3, align: 'center', weight: 900, alpha: fade * 0.9 });
  for (let j = 0; j < Math.min(3, passed.length); j++) {
    const m = passed[passed.length - 1 - j];
    const y = 1352 + (j - 1 + slide) * 56 + (j === 0 ? 56 * (1 - slide) * 0 : 0);
    const str = `${m.label} 約${fmtInt(m.km)}km`;
    if (j === 0) {
      const k = ease.back(seg(d, 0, 0.25));
      pillLabel(480, 1352, str + ' 通過', { size: 36, alpha: fade * seg(d, 0, 0.1), k, line: d < 1.2 ? C.cyan : 'rgba(61,224,255,0.45)' });
    } else {
      const a = fade * (j === 1 ? 0.62 : 0.34 * (1 - slide * 0.0));
      text('✓ ' + str, 480, y + 13, { size: 30, color: C.ink2, align: 'center', weight: 700, alpha: a * (j === 2 ? 1 - slide * 0.6 : 1) });
    }
  }
}
function drawCredit(t) {
  // 冒頭とループ直前は地球のドームと重なるので、そのあいだは少し上に出す
  const k = headerState(t) > 0.5 ? 1 : 0;
  text('音声 VOICEVOX:青山龍星 ｜ 出典 国立天文台VERA(2020)・NASA ｜ 距離は直線の概算', 480, k ? 1326 : 1478,
    { size: 22, color: C.ink3, align: 'center', weight: 500, alpha: 0.8 });
}

// ---------------------------------------------------------------- メイン
window.render = (t) => {
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.filter = 'none';
  drawBackground(t, SPEED_KEYS, seg(t, S.galaxy, 1) * (1 - seg(t, S.lap, 1)) * 0.6);
  const [sx, sy] = shakeAt(t);
  ctx.save(); ctx.translate(sx, sy);
  drawDome(t);
  const gb = galaxyBackdrop(t);
  sceneLap(t);
  drawVignette();
  const hs = headerState(t);
  sceneHook(t, hs);
  sceneSuspects(t);
  sceneSpin(t);
  sceneVerdict(t, 0, S.spinV, S.orbit, S.spinLane + 0.45);
  sceneOrbit(t);
  sceneVerdict(t, 1, S.orbitV, S.galaxy, S.orbitLane + 0.45);
  sceneGalaxy(t, gb);
  sceneVerdict(t, 2, S.galaxyV, isFinite(S.parker) ? S.parker : S.lap, S.match);
  sceneParker(t);
  sceneGoal(t);
  drawHeader(t);
  ctx.restore();
  drawMilestones(t);
  drawCredit(t);
  const f = flashAt(t);
  if (f > 0) { ctx.fillStyle = `rgba(255,255,255,${f})`; ctx.fillRect(0, 0, W, H); }
  drawTelop(t, TL);
};

// サムネイル用の 1 枚(冒頭の構図に大きい見出しを重ねる)
window.renderPoster = () => {
  const t = 2.215;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  drawBackground(t, SPEED_KEYS, 0);
  drawDome(t);
  drawVignette();
  sceneHook(t, 1);
  drawHeader(t);
  drawTelopChunk('じっとしてるのに', false, 1, { y: 1076, size: 92, maxW: 860, cx: 540 });
  drawTelopChunk('もう500km!?', true, 1, { y: 1262, size: 124, maxW: 900, cx: 540 });
};

// ブラウザで直接開いたときはプレビュー再生(?t=12.5 でその時刻の静止画)
if (!navigator.webdriver) {
  window.READY.then(() => {
    const q = new URLSearchParams(location.search);
    if (q.has('t')) return window.render(parseFloat(q.get('t')));
    const t0 = performance.now();
    const loop = () => { window.render(((performance.now() - t0) / 1000) % T_END); requestAnimationFrame(loop); };
    loop();
  });
}
