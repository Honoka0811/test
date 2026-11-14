// シーン構成とメイン描画。時刻はすべて build/timeline.js(ナレーション実測)から決まる。
const TL = window.TIMELINE;
const PLAN = buildPlan(TL), S = PLAN.S;
window.FPS = TL.fps || 60;
window.DURATION = TL.duration;
window.PLAN = PLAN;
window.READY = Promise.all([
  document.fonts.load('900 40px "Noto Sans JP"', 'あ漢1'), document.fonts.load('700 40px "Noto Sans JP"', 'あ漢1'),
  document.fonts.load('500 40px "Noto Sans JP"', 'あ漢1'),
  document.fonts.load('400 40px "Anton"', '0123'), Globe.load(),
]).then(() => document.fonts.ready);

const T_END = TL.duration;
const COL_SPIN = C.cyan, COL_ORB = C.orange, COL_GAL = C.yellow;
const OUT = 'rgba(3,6,26,0.9)';                 // 文字の縁取り色

// 背景の星が流れる速さ(シーンごとの「速さの感じ」に合わせる)
const SPEED_KEYS = [[0, 1050], [S.who, 1050], [S.spin - 0.2, 600], [S.spin + 0.5, 150], [S.orbit - 0.2, 150], [S.orbit + 0.5, 430],
  [S.zoom, 430], [S.zoom + 0.4, 1900], [S.galaxy, 1900], [S.galaxy + 0.6, 1400], [S.never - 0.2, 1400], [S.never + 0.4, 420],
  [S.goal, 420], [S.goal + 0.5, 1400], [T_END, 1800]];

// 画面を揺らす・光らせるタイミング
const HITS = [[S.hit500, 1], [S.spinLane + 0.5, 0.55], [S.orbitLane + 0.5, 0.55], [S.bridgeNo, 0.4], [S.galaxy, 1.0], [S.galaxySpeed, 0.6],
  [S.match, 0.8], [S.parkerWin, 0.6], [S.lapYears, 0.7], [S.humanFrac, 0.5], [S.yearNum, 0.5], [S.payoff, 1.0]].filter(h => isFinite(h[0]));
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
  // ループの継ぎ目: 最後の数フレームで光が立ち上がり、0 秒の頭で引いていく(12,742 → 0 の切り替わりをつなぐ)
  f = Math.max(f, 0.2 * Math.pow(seg(t, T_END - 0.12, 0.12), 2), 0.12 * Math.pow(1 - seg(t, 0, 0.12), 2));
  return f;
}
const pulseAt = (t, t0, dur = 0.35) => { const d = t - t0; return !(d >= 0) || d > dur ? 0 : Math.pow(1 - d / dur, 2); };

// ---------------------------------------------------------------- 小物
function chip(x, y, badge, title, color, alpha = 1, k = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x - 40 * (1 - k), y);
  const bw = measure(badge, 30, F.jp, 900) + 36;
  bar(0, -40, bw, 52, 26, color);
  text(badge, bw / 2, -3, { size: 30, color: '#06102e', align: 'center', weight: 900 });
  text(title, bw + 18, 2, { size: 52, color: C.ink, weight: 900, stroke: OUT, sw: 10 });
  ctx.restore();
}
// 「時速 1,360 km」のような大きい数字。y はベースライン
function bigNum(x, y, pre, num, unit, color, o = {}) {
  const { size = 140, alpha = 1, pop = 1, align = 'left', preSize = 44, sub = '', subColor = C.ink3, unitFamily = F.num, unitScale = 0.4 } = o;
  if (alpha <= 0) return;
  const uw = unitFamily === F.num ? 400 : 900;
  const wPre = pre ? measure(pre, preSize, F.jp, 900) + 12 : 0, wNum = measure(num, size, F.num, 400), wUnit = unit ? measure(unit, size * unitScale, unitFamily, uw) + 10 : 0;
  const total = wPre + wNum + wUnit;
  const x0 = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.translate(x0 + total / 2, y - size * 0.35); ctx.scale(pop, pop); ctx.translate(-(x0 + total / 2), -(y - size * 0.35));
  if (pre) text(pre, x0, y, { size: preSize, color: C.ink, stroke: OUT, sw: 10 });
  text(num, x0 + wPre, y, { size, family: F.num, weight: 400, color, stroke: OUT, sw: size * 0.09, glow: color, glowBlur: 26 });
  if (unit) text(unit, x0 + wPre + wNum + 10, y, { size: size * unitScale, family: unitFamily, weight: uw, color, stroke: OUT, sw: 8 });
  if (sub) text(sub, align === 'right' ? x : x0, y + 40, { size: 27, color: subColor, weight: 700, stroke: OUT, sw: 6, align: align === 'right' ? 'right' : 'left' });
  ctx.restore();
}
function pillLabel(cx, cy, str, o = {}) {
  const { size = 36, color = C.ink, fill = 'rgba(8,16,52,0.88)', line = C.cyan, alpha = 1, k = 1, icon = true } = o;
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
const pop = (t, t0, d = 0.3) => 0.8 + 0.2 * ease.back(seg(t, t0, d));
const fadeIn = (t, t0, d = 0.12) => seg(t, t0, d);

// ---------------------------------------------------------------- ヘッダー(メーターとゴール)
function headerState(t) { return clamp(1 - ease.inOut(seg(t, S.who - 0.12, 0.7))); }   // 1 = 中央の大きいメーター、0 = 上部ヘッダー
function drawHeader(t) {
  const h = headerState(t);
  const cx = 540, cy = lerp(480, 640, h), size = lerp(160, 340, h);
  const pz = pulseAt(t, S.hit500, 0.4) + pulseAt(t, S.noStop, 0.4) + pulseAt(t, S.match, 0.5) + pulseAt(t, S.k10000, 0.5) + pulseAt(t, S.payoff, 0.6)
    + seg(t, PLAN.GOAL_T - 0.1, 0.1);
  const box = drawOdometer(t, cx, cy, size * (1 + 0.05 * pz), { pulse: clamp(pz), crisp: t >= PLAN.GOAL_T - 1e-4 });
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
      text('何に対して？', box.right + 14, cy - 8, { size: 30, color: C.ink3, weight: 700, alpha: aHead * (1 - known) });
      text('→ このあと', box.right + 14, cy + 32, { size: 30, color: C.ink3, weight: 700, alpha: aHead * (1 - known) });
    }
    if (known > 0) {
      text('銀河の中心', box.right + 14, cy - 8, { size: 30, color: C.yellow, weight: 900, alpha: aHead * known });
      text('に対して', box.right + 14, cy + 32, { size: 30, color: C.yellow, weight: 900, alpha: aHead * known });
    }
    // ゴールゲージ(正体は最後まで伏せる。通過した天体の直径だけが刻まれていく)
    const gk = ease.out(seg(t, S.who + 0.25, 0.5));
    const done = t >= S.payoff;
    const near = seg(t, PLAN.GOAL_T - 7, 7);
    const pulse = pulseAt(t, S.teaseGoal, 0.6) + (done ? pulseAt(t, S.payoff, 0.8) + seg(t, PLAN.GOAL_T - 0.15, 0.15) : near * (0.5 + 0.5 * Math.sin(t * (6 + 10 * near))));
    ctx.save(); ctx.translate(0, -70 * (1 - gk));
    drawGauge(t, 328, {
      alpha: aHead * gk, goal: done ? '地球 1個ぶん' : '？？？ 1個ぶん', goalColor: done ? C.yellow : C.ink, goalPop: done ? pop(t, S.payoff, 0.3) : 1,
      pulse, ticks: PLAN.milestones.filter(m => m.planet),
      remain: t >= S.teaseGoal ? Math.max(0, Math.ceil(PLAN.GOAL_T - t - 1e-6)) : null,
    });
    ctx.restore();
  }
  return { h, box };
}

// ---------------------------------------------------------------- フック(0 秒〜)
// 画面下の地球と、日本に立つ「あなた」。点線は 0 秒のときに地球があった位置で、メーターと同じ縮尺で後ろへ離れていく。
const BACK = [-0.8, 0.6];                       // 置いていかれる向き(左下)。星の流れる向きと同じ
function drawDome(t) {
  const k = clamp(1 - ease.inOut(seg(t, S.who + 0.1, 1.0)));
  if (k <= 0) return;
  const p = drawEarthDome(1, (1 - k) * 640);
  if (!p) return;
  const off = 2 * p.r * V_GAL * t / EARTH_D, gx = p.cx + BACK[0] * off, gy = p.cy + BACK[1] * off;
  const ga = k * seg(t, 0.25, 0.3);
  ring(gx, gy, p.r, C.cyan, 4, ga * 0.9, [14, 12]);
  text('見始めた場所', gx - 250, gy - Math.sqrt(p.r * p.r - 250 * 250) - 14, { size: 30, color: C.cyan, align: 'center', weight: 900, alpha: ga, stroke: OUT, sw: 7 });
  const ph = (t * 1.1) % 1;
  ring(p.x, p.y, 12 + 44 * ph, C.red, 3, k * (1 - ph));
  ring(p.x, p.y, 12 + 44 * ((ph + 0.5) % 1), C.red, 3, k * (1 - (ph + 0.5) % 1));
  pin(p.x, p.y, 30, C.red, k);
  const tx = p.x + 38, ty = p.y - 58;
  text('あなた', tx, ty, { size: 50, color: C.ink, alpha: k, stroke: OUT, sw: 11 });
  const bx = tx + measure('あなた', 50) + 12;
  ctx.save(); ctx.globalAlpha *= k;
  rr(bx, ty - 42, 128, 52, 26); ctx.fillStyle = 'rgba(3,6,26,0.8)'; ctx.fill(); ctx.strokeStyle = C.cyan; ctx.lineWidth = 3; ctx.stroke();
  text('静止中', bx + 64, ty - 6, { size: 29, color: C.cyan, align: 'center', weight: 900 });
  ctx.restore();
}
function sceneHook(t, h, note = true) {
  const a = clamp((h - 0.55) / 0.45);
  if (a <= 0) return;
  const m0 = PLAN.milestones[0], sl = seg(t, m0.t - 0.1, 0.15);
  // 「何に対して?」の注記。最初の通過点(東京→大阪)が出たら、その下へ下がって残る
  if (note) text('※「何に対して？」の答えは このあと', 540, lerp(936, 1016, sl), { size: 34, color: C.ink3, align: 'center', weight: 700, alpha: a });
  if (t >= m0.t) pillLabel(540, 928, `${m0.label} 約${fmtInt(m0.km)}km 通過`, { size: 50, alpha: a * fadeIn(t, m0.t, 0.08), k: ease.back(seg(t, m0.t, 0.22)), line: C.cyan });
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
    const a = -tt * 1.6; circle(x + Math.cos(a) * 82, y + Math.sin(a) * 34, 12, '#3f9bff', 1, '#3f9bff', 14);
  } else {
    text('？', x, y + 44, { size: 124, family: F.jp, color: COL_GAL, align: 'center', glow: COL_GAL, glowBlur: 30 });
  }
}
function sceneSuspects(t) {
  const t0 = S.noStop + 0.1, a = inOut(t, S.who + 0.3, S.spin - 0.05, 0.3, 0.2);
  if (a <= 0) return;
  const ta = a * fadeIn(t, S.who + 0.5, 0.3);
  text('あなたを運んでいる', 540, 648, { size: 44, color: C.ink2, align: 'center', weight: 900, alpha: ta });
  text('犯人はだれ？', 540, 726, { size: 72, color: C.ink, align: 'center', alpha: ta, stroke: OUT, sw: 10 });
  const names = ['自転', '公転', '？？？'], subs = ['地球が回る', '太陽を回る', '………'], cols = [COL_SPIN, COL_ORB, COL_GAL];
  for (let i = 0; i < 3; i++) {
    const k = ease.back(seg(t, t0 + i * 0.2, 0.32)), ka = seg(t, t0 + i * 0.2, 0.12);
    if (ka <= 0) continue;
    const x = 60 + i * 278, y = 768, w = 266, hh = 318;
    ctx.save(); ctx.globalAlpha *= a * ka; ctx.translate(x + w / 2, y + hh / 2); ctx.scale(0.8 + 0.2 * k, 0.8 + 0.2 * k); ctx.translate(-w / 2, -hh / 2);
    panel(0, 0, w, hh, 28, 1, C.panel, cols[i], 3);
    bar(w / 2 - 78, 18, 156, 44, 22, cols[i]);
    text('容疑者 ' + (i + 1), w / 2, 51, { size: 28, color: '#06102e', align: 'center' });
    suspectIcon(i, w / 2, 150, t - t0);
    text(names[i], w / 2, 262, { size: 56, color: C.ink, align: 'center' });
    text(subs[i], w / 2, 304, { size: 30, color: C.ink2, align: 'center', weight: 700 });
    ctx.restore();
  }
}

// ---------------------------------------------------------------- 容疑者1: 自転
function sceneSpin(t) {
  const a = inOut(t, S.spin - 0.05, S.spinV - 0.05, 0.3, 0.2);
  if (a <= 0) return;
  const tt = t - S.spin, k = ease.out(seg(t, S.spin, 0.5));
  chip(70, 632, '容疑者 1', '地球の自転', COL_SPIN, a, k);
  const gx = 292, gy = 880, r = 190 * (0.85 + 0.15 * k), lon0 = 172 - tt * 8.5, lat0 = 22;
  drawGlobe(gx, gy, r, lon0, lat0, a);
  arcArrow(gx, gy, r + 24, Math.PI * 1.22, Math.PI * 1.78, COL_SPIN, 7, a * k);
  text('東へ', gx + (r + 24) * 0.771 + 20, gy - (r + 24) * 0.637 + 4, { size: 30, color: COL_SPIN, alpha: a * k, weight: 900, stroke: OUT, sw: 6 });
  const p = Globe.project(35.68, 139.77, lon0, lat0, r);
  if (p.visible) {
    const px = gx + p.x, py = gy + p.y, ph = (t * 1.4) % 1;
    ring(px, py, 10 + 30 * ph, C.red, 3, a * (1 - ph));
    circle(px, py, 9, C.red, a, C.red, 18);
    text('東京', px + 6, py - 20, { size: 34, color: C.ink, alpha: a, align: 'center', stroke: OUT, sw: 8 });
  }
  text('東京の地面は', 560, 760, { size: 38, color: C.ink2, alpha: a * fadeIn(t, S.spinSpeed - 0.6, 0.25), weight: 900 });
  bigNum(560, 890, '時速', '1,360', 'km', COL_SPIN, { size: 124, alpha: a * fadeIn(t, S.spinSpeed - 0.05), pop: pop(t, S.spinSpeed - 0.05), sub: '（地球の中心に対して）' });
  // 音速との比較(右のボタン列にかからない幅で)
  const bA = a * fadeIn(t, S.sound - 0.05, 0.2);
  if (bA > 0) {
    const x0 = 560, wMax = 230, g = ease.out(seg(t, S.sound - 0.05, 0.45));
    text('音速', x0, 1002, { size: 30, color: C.ink2, alpha: bA, weight: 900 });
    bar(x0 + 100, 974, wMax * (1225 / 1360) * g, 34, 17, 'rgba(255,255,255,0.78)', bA);
    text('1,225', x0 + 100 + wMax * (1225 / 1360) * g - 10, 1002, { size: 30, family: F.num, weight: 400, color: '#06102e', align: 'right', alpha: bA * seg(g, 0.6, 0.4) });
    text('東京', x0, 1048, { size: 30, color: COL_SPIN, alpha: bA, weight: 900 });
    bar(x0 + 100, 1020, wMax * g, 34, 17, COL_SPIN, bA, COL_SPIN);
    text('1,360', x0 + 100 + wMax * g - 10, 1048, { size: 30, family: F.num, weight: 400, color: '#06102e', align: 'right', alpha: bA * seg(g, 0.6, 0.4) });
    text('時速km ／ 音速は気温15℃', x0, 1084, { size: 21, color: C.ink3, alpha: bA, weight: 700 });
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
  const tx0 = 250, tw = 430, VX = 890;         // 値の右端(右のボタン列を避ける)
  lineSeg(tx0 + tw, 714, tx0 + tw, 1062, 'rgba(255,225,74,0.7)', 3, 1, [8, 8]);       // メーター(100%)の基準線
  text('メーター', tx0 + tw, 706, { size: 30, color: C.yellow, align: 'center', weight: 900 });
  const bridge = idx === 1 && t >= S.bridge - 0.05;   // 「2つ足しても足りない」
  for (let i = 0; i < 3; i++) {
    const R = ROWS[i], y = 770 + i * 108, isNew = i === idx, future = i > idx;
    if (future) {                                // まだ調べていない容疑者
      ctx.save(); ctx.globalAlpha *= 0.4;
      text(i === 2 ? '？？？' : R.name, 150, y + 16, { size: 46, color: C.ink2 });
      bar(tx0, y - 26, tw, 54, 27, 'rgba(255,255,255,0.09)');
      text('—', VX, y + 18, { size: 50, family: F.num, weight: 400, color: C.ink3, align: 'right' });
      ctx.restore();
      if (bridge && i === 2) {                   // 残り 87% を説明できるのはだれか
        const ba = fadeIn(t, S.bridgeNo, 0.15), bk = pop(t, S.bridgeNo, 0.3), x87 = tx0 + tw * 0.133;
        ctx.save(); ctx.globalAlpha *= ba * (0.75 + 0.25 * Math.sin(t * 14));
        rr(x87, y - 26, tw - (x87 - tx0), 54, 12); ctx.fillStyle = 'rgba(255,75,75,0.30)'; ctx.fill(); ctx.strokeStyle = C.red; ctx.lineWidth = 3; ctx.setLineDash([10, 8]); ctx.stroke();
        ctx.restore();
        text('87%も足りない', x87 + (tw - (x87 - tx0)) / 2, y + 15, { size: 40 * bk, color: '#fff', align: 'center', alpha: ba, stroke: OUT, sw: 9 });
      }
      continue;
    }
    const g = isNew ? ease.out(seg(t, tIn + 0.1, i === 2 ? Math.max(0.2, tStamp - tIn - 0.12) : 0.5)) : 1;
    const stamped = !isNew || t >= tStamp, sk = isNew ? ease.back(seg(t, tStamp, 0.25)) : 1;
    const jx = isNew && i < 2 ? 10 * pulseAt(t, tStamp, 0.3) * Math.sin((t - tStamp) * 90) : 0;
    ctx.save(); ctx.translate(jx, 0);
    if (isNew && !stamped) { ctx.save(); ctx.globalAlpha *= 0.5 + 0.5 * Math.sin(t * 9); rr(70, y - 46, 840, 94, 20); ctx.strokeStyle = R.col; ctx.lineWidth = 3; ctx.stroke(); ctx.restore(); }
    text(R.name, 150, y + 16, { size: 46, color: C.ink, align: 'left' });
    bar(tx0, y - 26, tw, 54, 27, 'rgba(255,255,255,0.09)');
    bar(tx0, y - 26, Math.max(i === 0 ? 7 : 12, tw * (R.v / V_GAL) * g), 54, i === 0 ? 3.5 : 27, R.col, 1, R.col);
    const dist = R.v * t, val = (R.dec ? dist.toFixed(1) : fmtInt(dist));
    text(val, VX - measure('km', 30, F.num, 400) - 8, y + 22, { size: 62, family: F.num, weight: 400, color: R.col, align: 'right' });
    text('km', VX, y + 22, { size: 30, family: F.num, weight: 400, color: R.col, align: 'right' });
    if (stamped) { if (i < 2) markCross(110, y, 20 * sk, C.red, 9, 1); else markCheck(108, y, 24 * sk, C.green, 10, 1); }
    ctx.restore();
  }
  if (t >= tStamp) {                             // 判定の言葉
    const sk = ease.back(seg(t, tStamp, 0.25)), y = 770 + idx * 108, sa = fadeIn(t, tStamp, 0.1);
    if (idx < 2) text('足りない', tx0 + tw * 0.5, y + 16, { size: 44 * (0.7 + 0.3 * sk), color: C.red, align: 'center', alpha: sa, stroke: 'rgba(3,6,26,0.95)', sw: 10 });
    else text('メーターと一致', tx0 + tw * 0.5, y + 15, { size: 42 * (0.7 + 0.3 * sk), color: '#06102e', align: 'center', alpha: sa });
  }
  if (bridge) {                                  // 自転 + 公転 = メーターの 13%
    const ba = fadeIn(t, S.bridge, 0.2);
    ctx.save(); ctx.globalAlpha *= ba; ctx.strokeStyle = '#fff'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(tx0 + 86, 750); ctx.lineTo(tx0 + 104, 750); ctx.lineTo(tx0 + 104, 898); ctx.lineTo(tx0 + 86, 898); ctx.stroke(); ctx.restore();
    text('2つ合わせて 13%', tx0 + 118, 836, { size: 34, color: '#fff', alpha: ba, stroke: OUT, sw: 8 });
  }
  ctx.restore();
}

// ---------------------------------------------------------------- 容疑者2: 公転
function sceneOrbit(t) {
  const a = inOut(t, S.orbit - 0.05, S.orbitV - 0.05, 0.3, 0.2);
  if (a <= 0) return;
  const tt = t - S.orbit, k = ease.out(seg(t, S.orbit, 0.5));
  chip(70, 632, '容疑者 2', '地球の公転', COL_ORB, a, k);
  const cx = 540, cy = 842, rx = 390 * (0.8 + 0.2 * k), ry = 100 * (0.8 + 0.2 * k);
  const ang = 0.1 - tt * 0.66, ex = cx + Math.cos(ang) * rx, ey = cy + Math.sin(ang) * ry;
  const orbitHalf = (front) => {
    ctx.save(); ctx.globalAlpha *= a * 0.85; ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 5; ctx.setLineDash([5, 13]); ctx.lineCap = 'round';
    ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, front ? 0 : Math.PI, front ? Math.PI : Math.PI * 2); ctx.stroke(); ctx.restore();
  };
  const earth = () => {
    ctx.save(); ctx.lineCap = 'round';
    for (let i = 0; i < 26; i++) {
      const a0 = ang + i * 0.035, a1 = a0 + 0.035;
      ctx.globalAlpha = a * (1 - i / 26) * 0.9; ctx.strokeStyle = COL_ORB; ctx.lineWidth = 18 * (1 - i / 30);
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a0) * rx, cy + Math.sin(a0) * ry); ctx.lineTo(cx + Math.cos(a1) * rx, cy + Math.sin(a1) * ry); ctx.stroke();
    }
    ctx.restore();
    drawGlobe(ex, ey, 42, 140 - tt * 40, 15, a, 0.8);
    text('地球', ex, ey - 54, { size: 30, color: C.ink, align: 'center', alpha: a, stroke: OUT, sw: 7 });
  };
  const behind = Math.sin(ang) < 0;
  orbitHalf(false);
  if (behind) earth();
  glowBlob(cx, cy, 230, 'rgba(255,170,40,0.55)', a); glowBlob(cx, cy, 110, 'rgba(255,240,180,0.9)', a);
  circle(cx, cy, 54, rgrad(cx - 12, cy - 12, 4, 58, [[0, '#FFF8D8'], [1, '#FFB52E']]), a);
  text('太陽', cx, cy + 100, { size: 30, color: C.ink, align: 'center', alpha: a, stroke: OUT, sw: 7 });
  orbitHalf(true);
  if (!behind) earth();
  const sA = a * fadeIn(t, S.orbitSpeed - 0.05);
  bigNum(1010, 716, '秒速 約', '30', 'km', COL_ORB, { size: 132, alpha: sA, pop: pop(t, S.orbitSpeed - 0.05), align: 'right' });
  text('（太陽に対して・平均 約29.8km）', 1010, 756, { size: 25, color: C.ink3, align: 'right', alpha: sA, weight: 700, stroke: OUT, sw: 6 });
  // 東京→大阪(直線 約400km)を、公転の速さとメーターの速さで走らせる
  const rA = a * fadeIn(t, S.osaka - 0.05, 0.25);
  if (rA > 0) {
    const x0 = 250, x1 = 770, w = x1 - x0, dt = Math.max(0, t - S.osaka), yM = 1010, yO = 1060;
    ctx.save(); ctx.globalAlpha *= rA;
    text('東京', x0, 972, { size: 26, color: C.ink, align: 'center', weight: 900, stroke: OUT, sw: 6 });
    text('大阪', x1, 972, { size: 26, color: C.ink, align: 'center', weight: 900, stroke: OUT, sw: 6 });
    text('約400km', (x0 + x1) / 2, 972, { size: 22, color: C.ink3, align: 'center', weight: 700 });
    for (const [y, col, name] of [[yM, C.yellow, 'メーター'], [yO, COL_ORB, '公転']]) {
      lineSeg(x0, y, x1, y, 'rgba(255,255,255,0.22)', 6);
      lineSeg(x0, y - 12, x0, y + 12, '#fff', 3); lineSeg(x1, y - 12, x1, y + 12, '#fff', 3);
      text(name, x0 - 20, y + 10, { size: 28, color: col, align: 'right', weight: 900, stroke: OUT, sw: 6 });
    }
    const fm = (dt * V_GAL / 400) % 1, xm = x0 + w * fm;                // メーター: 約 1.8 秒で走り抜け、何度も通る
    ctx.save(); ctx.strokeStyle = grad(xm - 110, 0, xm, 0, [[0, 'rgba(255,225,74,0)'], [1, C.yellow]]); ctx.lineWidth = 8; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(Math.max(x0, xm - 110), yM); ctx.lineTo(xm, yM); ctx.stroke(); ctx.restore();
    circle(xm, yM, 11, '#fff', 1, C.yellow, 20);
    const xo = x0 + w * Math.min(1, dt * V_ORB / 400);                  // 公転: 約 13 秒かかる
    lineSeg(x0, yO, xo, yO, COL_ORB, 8);
    circle(xo, yO, 11, '#fff', 1, COL_ORB, 20);
    const tA = fadeIn(t, S.osakaSec - 0.05), tP = pop(t, S.osakaSec - 0.05);
    text('約1.8秒', x1 + 22, yM + 10, { size: 28, color: C.yellow, weight: 900, alpha: tA, stroke: OUT, sw: 6 });
    text('約13秒', x1 + 22, yO + 12, { size: 34 * tP, color: COL_ORB, weight: 900, alpha: tA, stroke: OUT, sw: 7 });
    ctx.restore();
  }
}

// ---------------------------------------------------------------- 容疑者3: 銀河
function galaxyBackdrop(t) {
  // 「天の川銀河だ」の瞬間に画面いっぱいへ広がり、太陽系の位置を示すころに落ち着く。判定のあいだも背景に残す
  const a = inOut(t, S.galaxy - 0.02, S.tease + 0.35, 0.06, 0.5);
  const burst = ease.out5(seg(t, S.galaxy, 0.55)), settle = ease.inOut(seg(t, S.galaxy + 0.55, Math.max(0.3, S.solar - S.galaxy - 0.65)));
  const dim = 1 - 0.62 * seg(t, S.galaxyV - 0.1, 0.4);
  const R = lerp(lerp(140, 900, burst), 600, settle), rot = 0.5 + (t - S.galaxy) * 0.085;
  const sun = drawGalaxy(540, 850, R, rot, { alpha: Math.max(0, a) * dim, bright: 1.25 });
  return { sun, R, a, dim };
}
function sceneZoomOut(t) {
  // 「真犯人は、もっと大きい」: 太陽と地球の軌道が 1 点に縮み、暗い空間に取り残される
  const a = inOut(t, S.zoom - 0.05, S.galaxy + 0.03, 0.25, 0.06);
  if (a <= 0) return;
  const s = lerp(1, 0.012, ease.out(seg(t, S.zoom, Math.max(0.6, S.bigger - S.zoom + 0.25))));
  const x = 540, y = 850, ph = (t * 1.3) % 1;
  ctx.save(); ctx.globalAlpha *= a;
  if (s > 0.02) { ctx.strokeStyle = 'rgba(255,255,255,0.75)'; ctx.lineWidth = 4; ctx.beginPath(); ctx.ellipse(x, y, 390 * s, 100 * s, 0, 0, 6.2832); ctx.stroke(); }
  else ring(x, y, 10 + 40 * ph, '#FFE9A8', 3, 1 - ph);
  circle(x, y, Math.max(6, 54 * s), '#FFE9A8', 1, '#FFB52E', 30);
  text('太陽系', x, y - 36 - 110 * s, { size: 40, color: C.ink, align: 'center', stroke: OUT, sw: 9 });
  const qa = fadeIn(t, S.bigger, 0.2), qp = pop(t, S.bigger, 0.3);
  text('？', x, y + 250, { size: 190 * qp, color: 'rgba(255,225,74,0.9)', align: 'center', alpha: qa, glow: C.yellow, glowBlur: 40 });
  ctx.restore();
}
function sceneGalaxy(t, gb) {
  const a = inOut(t, S.galaxy - 0.05, S.galaxyV - 0.05, 0.2, 0.2);
  if (a <= 0 || !gb) return;
  chip(70, 632, '容疑者 3', '天の川銀河', COL_GAL, a * fadeIn(t, S.galaxy + 0.25, 0.2), ease.out(seg(t, S.galaxy + 0.25, 0.4)));
  // 太陽系の位置と、銀河の中心をまわる軌道
  const oa = a * fadeIn(t, S.solar - 0.1, 0.3);
  const [sx, sy] = gb.sun, ph = (t * 1.2) % 1;
  if (t >= S.turning - 0.1) {
    const sweep = ease.inOut(seg(t, S.turning - 0.1, 1.0));
    ctx.save(); ctx.globalAlpha *= a * 0.9 * sweep; ctx.strokeStyle = COL_GAL; ctx.lineWidth = 3.5; ctx.setLineDash([10, 12]); ctx.lineCap = 'round';
    galaxyOrbitPath(540, 850, gb.R); ctx.stroke(); ctx.restore();
  }
  ring(sx, sy, 12 + 34 * ph, COL_GAL, 3, oa * (1 - ph));
  circle(sx, sy, 10, '#fff', oa, COL_GAL, 26);
  lineSeg(sx + 10, sy - 10, sx + 62, sy - 62, 'rgba(255,255,255,0.8)', 2.5, oa);
  text('太陽系', sx + 70, sy - 74, { size: 40, color: C.ink, alpha: oa, stroke: OUT, sw: 9 });
  text('（あなたはここ）', sx + 70, sy - 36, { size: 30, color: COL_GAL, alpha: oa, weight: 900, stroke: OUT, sw: 7 });
  text('銀河の中心', 540, 850 + 74, { size: 28, color: C.ink2, align: 'center', alpha: oa, weight: 900, stroke: OUT, sw: 6 });
  const sA = a * fadeIn(t, S.galaxySpeed - 0.05);
  bigNum(1010, 724, '秒速およそ', '227', 'km', COL_GAL, { size: 132, alpha: sA, pop: pop(t, S.galaxySpeed - 0.05), preSize: 38, align: 'right' });
  text('銀河の中心に対して ／ 出典 国立天文台 VERA（2020）', 1010, 1044, { size: 25, color: C.ink2, align: 'right', alpha: sA, weight: 700, stroke: OUT, sw: 6 });
}

// ---------------------------------------------------------------- ゴールの予告(正体は伏せたまま)
function sceneTease(t) {
  const a = inOut(t, S.tease - 0.05, S.parker - 0.05, 0.25, 0.2);
  if (a <= 0) return;
  const k = ease.out(seg(t, S.tease, 0.4)), p = clamp(V_GAL * t / EARTH_D);
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(0, 30 * (1 - k));
  panel(50, 610, 980, 474, 30, 1);
  text('残るは', 86, 680, { size: 40, color: C.ink2, weight: 900 });
  text('ゴール', 86 + measure('残るは', 40) + 18, 688, { size: 76 * pop(t, S.teaseGoal, 0.3), color: C.yellow, alpha: fadeIn(t, S.teaseGoal), stroke: OUT, sw: 10, glow: C.yellow });
  // 大きいゲージ
  const x0 = 96, x1 = 680, y = 810, h = 48, w = x1 - x0;
  bar(x0, y, w, h, h / 2, 'rgba(255,255,255,0.10)');
  bar(x0, y, Math.max(h, w * p), h, h / 2, grad(x0, 0, x1, 0, [[0, '#FF8A00'], [1, C.yellow]]), 1, 'rgba(255,200,40,0.8)');
  for (const m of PLAN.milestones.filter(m => m.planet)) {
    const tx = x0 + w * m.km / EARTH_D, passed = t >= m.t;
    lineSeg(tx, y - 10, tx, y + h + 10, passed ? '#fff' : 'rgba(255,255,255,0.4)', 3);
    text(passed ? m.short : '？', tx, y - 22, { size: 30, color: passed ? C.ink : C.ink3, align: 'center', weight: 900 });
  }
  circle(x0 + Math.max(h, w * p) - h / 2, y + h / 2, 13, '#fff', 1, '#fff', 22);
  // ゴールにある「あるもの」(コインのように回る黒い円)
  const gx = 792, gy = y + h / 2, sp = t >= S.teaseThing ? Math.cos((t - S.teaseThing) * 9) * (1 - seg(t, S.teaseOne, 0.3)) + seg(t, S.teaseOne, 0.3) : 1;
  ctx.save(); ctx.translate(gx, gy); ctx.scale(Math.abs(sp) * 0.9 + 0.1, 1);
  circle(0, 0, 70, 'rgba(4,8,30,0.95)'); ring(0, 0, 70, C.yellow, 5, 1, [12, 10]);
  text('？', 0, 40, { size: 110, color: C.yellow, align: 'center', glow: C.yellow });
  ctx.restore();
  text('？？？ 1個ぶん', gx, gy + 116, { size: 31 * pop(t, S.teaseOne, 0.3), color: C.ink, align: 'center', alpha: fadeIn(t, S.teaseOne), stroke: OUT, sw: 8 });
  // 残り時間
  const rem = Math.max(0, Math.ceil(PLAN.GOAL_T - t - 1e-6)), ca = fadeIn(t, S.teaseGoal + 0.1, 0.2);
  text('ゴールまで', 96, 1010, { size: 40, color: C.ink2, weight: 900, alpha: ca });
  bigNum(96 + measure('ゴールまで', 40) + 18, 1024, 'あと', String(rem), '秒', C.yellow, { size: 108, alpha: ca, preSize: 40, unitFamily: F.jp, unitScale: 0.42 });
  ctx.restore();
}

// ---------------------------------------------------------------- 人類最速の探査機の記録との比較
function probeIcon(x, y, s, alpha) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x, y);
  ctx.fillStyle = '#5aa0ff'; ctx.fillRect(-s * 0.75, -s * 0.85, s * 0.5, s * 0.5); ctx.fillRect(-s * 0.75, s * 0.35, s * 0.5, s * 0.5);   // 太陽電池
  ctx.fillStyle = '#e8ecff'; rr(-s * 0.95, -s * 0.26, s * 1.05, s * 0.52, 5); ctx.fill();                       // 本体
  ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.moveTo(s * 0.1, -s * 0.2); ctx.lineTo(s * 0.5, -s * 0.66); ctx.lineTo(s * 0.62, -s * 0.66);
  ctx.lineTo(s * 0.62, s * 0.66); ctx.lineTo(s * 0.5, s * 0.66); ctx.lineTo(s * 0.1, s * 0.2); ctx.closePath(); ctx.fill();     // 耐熱シールド(円すい)
  ctx.restore();
}
function sceneParker(t) {
  const a = inOut(t, S.parker - 0.05, S.lap - 0.05, 0.25, 0.2);
  if (a <= 0) return;
  const k = ease.out(seg(t, S.parker, 0.4));
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(0, 30 * (1 - k));
  panel(50, 610, 980, 474, 30, 1);
  text('人類最速の探査機の「記録」と比べると', 86, 674, { size: 38, color: C.ink, weight: 900 });
  const x0 = 86, wMax = 800;
  const g1 = ease.out(seg(t, S.parker + 0.15, 0.6)), w1 = Math.max(30, wMax * (192 / 227) * g1);
  text('パーカー・ソーラー・プローブ', x0, 744, { size: 32, color: C.ink, weight: 900 });
  text('太陽に対して｜2024年12月・NASA', x0 + 470, 744, { size: 23, color: C.ink3, weight: 700 });
  bar(x0, 760, w1, 62, 16, grad(x0, 0, x0 + wMax, 0, [[0, '#1c6dff'], [1, C.cyan]]), 1, C.cyan);
  probeIcon(x0 + w1 + 46, 791, 40, g1);
  text('秒速 約192km', x0 + 22, 803, { size: 36, color: '#04102e', weight: 900, alpha: seg(g1, 0.5, 0.5) });
  const g2 = ease.out(seg(t, S.parkerRec, Math.max(0.5, S.parkerWin - S.parkerRec + 0.1))), w2 = Math.max(30, wMax * g2);
  text('あなた（太陽系ごと）', x0, 906, { size: 32, color: COL_GAL, weight: 900 });
  text('銀河の中心に対して', x0 + 330, 906, { size: 23, color: C.ink3, weight: 700 });
  bar(x0, 922, w2, 62 + 6 * pulseAt(t, S.parkerWin, 0.4), 16, grad(x0, 0, x0 + wMax, 0, [[0, '#FF8A00'], [1, C.yellow]]), 1, C.yellow);
  text('秒速 およそ227km', x0 + 22, 965, { size: 36, color: '#04102e', weight: 900, alpha: seg(g2, 0.5, 0.5) });
  pin(x0 + w2 + 26, 975, 22, COL_GAL, g2);
  const dA = fadeIn(t, S.parkerWin, 0.1), dP = pop(t, S.parkerWin, 0.3);        // 差を見せる
  lineSeg(x0 + wMax * (192 / 227), 838, x0 + wMax * (192 / 227), 916, '#fff', 3, dA, [6, 6]);
  text('＋35km/s', x0 + wMax, 884, { size: 40 * dP, color: C.yellow, align: 'right', alpha: dA, stroke: OUT, sw: 8, glow: C.yellow });
  text('※「何に対する速さか」がちがう数字を、そのまま並べた比較です', x0, 1048, { size: 24, color: C.ink3, weight: 700 });
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
// 首の長い恐竜のシルエット(竜脚類ふう。x, y は胴の中心、s は全体の倍率)
function dinoShape(x, y, s, color, alpha) {
  if (alpha <= 0 || s <= 0.01) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x, y); ctx.scale(s, s);
  ctx.fillStyle = color; ctx.strokeStyle = color; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.shadowColor = color; ctx.shadowBlur = 26;
  ctx.beginPath(); ctx.ellipse(0, 0, 112, 60, -0.05, 0, 6.2832); ctx.fill();                                  // 胴
  ctx.lineWidth = 40; ctx.beginPath(); ctx.moveTo(78, -22); ctx.quadraticCurveTo(150, -60, 186, -168); ctx.stroke();   // 首
  ctx.beginPath(); ctx.ellipse(204, -184, 34, 19, -0.35, 0, 6.2832); ctx.fill();                              // 頭
  ctx.lineWidth = 36; ctx.beginPath(); ctx.moveTo(-88, -6); ctx.quadraticCurveTo(-170, -8, -214, 30); ctx.stroke();    // しっぽ(根元)
  ctx.lineWidth = 16; ctx.beginPath(); ctx.moveTo(-200, 18); ctx.quadraticCurveTo(-250, 50, -292, 44); ctx.stroke();   // しっぽ(先)
  ctx.shadowBlur = 0;
  for (const lx of [-74, -34, 40, 78]) { rr(lx - 17, 24, 34, 104, 12); ctx.fill(); }                           // 脚
  ctx.restore();
}
function sceneLap(t) {
  const a = inOut(t, S.lap - 0.05, S.year - 0.05, 0.35, 0.25);
  if (a <= 0) return;
  const cx = 540, cy = 860, k = ease.out(seg(t, S.lap, 0.6)), R = 400 * (0.9 + 0.1 * k), rot = 1.1 + (t - S.lap) * 0.05;
  const sun = drawGalaxy(cx, cy, R, rot, { tilt: 1, ang: 0, alpha: a * 0.62, bright: 1.0 });
  const rr0 = GALAXY.sun.r * R, sa = Math.atan2(sun[1] - cy, sun[0] - cx);
  ring(cx, cy, rr0, 'rgba(255,225,74,0.45)', 3, a, [6, 10]);
  const lp = ease.inOut(seg(t, S.lap + 0.2, Math.max(1.0, S.lapYears - S.lap + 0.4)));   // 1 周をなぞる光
  ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = COL_GAL; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.shadowColor = COL_GAL; ctx.shadowBlur = 18;
  ctx.beginPath(); ctx.arc(cx, cy, rr0, sa, sa - Math.PI * 2 * lp, true); ctx.stroke(); ctx.restore();
  const hA = a * fadeIn(t, S.human + 0.05, 0.3);
  circle(sun[0], sun[1], 11, '#fff', a, COL_GAL, 26);
  text('太陽系', sun[0], sun[1] - 24, { size: 30, color: C.ink, align: 'center', alpha: a * (1 - fadeIn(t, S.human + 0.05, 0.3)), stroke: OUT, sw: 7 });
  // 1 周 = およそ 2 億年
  const yA = a * fadeIn(t, S.lapYears - 0.05);
  text('銀河を1周', 70, 628, { size: 38, color: C.ink2, alpha: a * fadeIn(t, S.lap + 0.1, 0.3), weight: 900, stroke: OUT, sw: 8 });
  ctx.save(); ctx.globalAlpha *= yA; ctx.translate(70, 768); ctx.scale(pop(t, S.lapYears - 0.05), pop(t, S.lapYears - 0.05));
  const w0 = text('およそ', 0, 0, { size: 40, color: C.ink, stroke: OUT, sw: 9 });
  const w1 = text('2', w0 + 12, 4, { size: 120, family: F.num, weight: 400, color: COL_GAL, stroke: OUT, sw: 11, glow: COL_GAL });
  text('億年', w0 + w1 + 22, 0, { size: 72, color: COL_GAL, stroke: OUT, sw: 11 });
  ctx.restore();
  text('中心まで約2万5800光年・秒速227kmで計算', 70, 810, { size: 21, color: C.ink3, alpha: yA, weight: 700, stroke: OUT, sw: 5 });
  // 1 周前
  const dA = a * fadeIn(t, S.dino + 0.1, 0.25);
  text('1周前（約2.1億年前）', 1010, 646, { size: 32, color: C.ink2, align: 'right', alpha: dA, weight: 900, stroke: OUT, sw: 7 });
  const wA = a * fadeIn(t, S.dinoWord - 0.05), dk = pop(t, S.dinoWord - 0.05);
  text('恐竜が現れたころ', 1010, 708, { size: 48 * dk, color: C.green, align: 'right', alpha: wA, stroke: OUT, sw: 10 });
  text('三畳紀｜「ここ」＝銀河の中心から見て同じ方向', 1010, 746, { size: 21, color: C.ink3, align: 'right', alpha: wA, weight: 700, stroke: OUT, sw: 5 });
  const gone = seg(t, S.human - 0.05, 0.25);
  dinoShape(790, 930, (0.6 + 0.4 * ease.back(seg(t, S.dinoWord - 0.05, 0.35))) * (1 - ease.in(gone)), C.green, wA * (1 - gone));
  footprint(1010 - 48 * 8 - 46, 692, 26, C.green, wA);
  ring(sun[0], sun[1], 22 + 10 * Math.sin(t * 6), C.green, 4, wA * (1 - gone));
  // 人類の歴史 = 1 周の約 1/700
  const lx = 810, ly = 980, lr = 90;
  if (hA > 0) {
    lineSeg(sun[0], sun[1], lx - lr * 0.72, ly - lr * 0.72, 'rgba(255,255,255,0.7)', 2.5, hA);
    ctx.save(); ctx.globalAlpha *= hA;
    circle(lx, ly, lr, 'rgba(6,12,44,0.94)'); ring(lx, ly, lr, '#fff', 4, 1);
    ctx.save(); ctx.beginPath(); ctx.arc(lx, ly, lr - 3, 0, 6.2832); ctx.clip();
    ctx.strokeStyle = 'rgba(255,225,74,0.55)'; ctx.lineWidth = 12; ctx.beginPath(); ctx.arc(lx - 30, ly + 600, 610, -Math.PI * 0.62, -Math.PI * 0.38); ctx.stroke();
    const g = ease.out(seg(t, S.humanFrac - 0.05, 0.4));
    ctx.strokeStyle = C.pink; ctx.lineWidth = 12; ctx.lineCap = 'round'; ctx.shadowColor = C.pink; ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.arc(lx - 30, ly + 600, 610, -Math.PI * 0.5 - 0.012 * g, -Math.PI * 0.5 + 0.012 * g); ctx.stroke();
    ctx.restore();
    text('拡大', lx, ly + lr - 16, { size: 22, color: C.ink2, align: 'center', weight: 900 });
    ctx.restore();
  }
  text('人類（ホモ・サピエンス）約30万年', 70, 950, { size: 30, color: C.ink2, alpha: hA, weight: 900, stroke: OUT, sw: 8 });
  const fA = a * fadeIn(t, S.humanFrac - 0.05), fP = pop(t, S.humanFrac - 0.05);
  ctx.save(); ctx.globalAlpha *= fA; ctx.translate(70, 1044); ctx.scale(fP, fP);
  const v0 = text('1周の 約', 0, 0, { size: 42, color: C.ink, stroke: OUT, sw: 9 });
  text('1/700', v0 + 14, 4, { size: 84, family: F.num, weight: 400, color: C.pink, stroke: OUT, sw: 10, glow: C.pink });
  ctx.restore();
}

// ---------------------------------------------------------------- 1 年で進む距離
function sceneYear(t) {
  const a = inOut(t, S.year - 0.05, S.never - 0.05, 0.25, 0.2);
  if (a <= 0) return;
  const k = ease.out(seg(t, S.year, 0.4));
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(0, 24 * (1 - k));
  text('あなたが 1年で進む距離', 70, 650, { size: 42, color: C.ink2, weight: 900, stroke: OUT, sw: 8 });
  const x0 = 120, per = 11.0, y = 850, X = (oku) => x0 + oku * per;   // 1 億 km = 11px
  lineSeg(x0, y, 1010, y, 'rgba(255,255,255,0.28)', 6);
  glowBlob(x0, y, 120, 'rgba(255,190,60,0.7)'); circle(x0, y, 26, rgrad(x0 - 6, y - 6, 2, 28, [[0, '#FFF8D8'], [1, '#FFB52E']]));
  text('太陽', x0, y + 66, { size: 28, color: C.ink, align: 'center', weight: 900, stroke: OUT, sw: 6 });
  [['木星', 7.8, -1], ['土星', 14.3, 1], ['天王星', 28.7, -1], ['海王星', 45.0, -1]].forEach(([name, oku, side], i) => {
    const pa = fadeIn(t, S.year + 0.15 + i * 0.1, 0.15), nep = name === '海王星';
    lineSeg(X(oku), y - 16, X(oku), y + 16, nep ? C.cyan : '#fff', nep ? 5 : 3, pa);
    text(name, X(oku), side < 0 ? y - 30 : y + 52, { size: nep ? 32 : 28, color: nep ? C.cyan : C.ink2, align: 'center', weight: 900, alpha: pa, stroke: OUT, sw: 6 });
  });
  text('約45億km', X(45.0), y + 52, { size: 28, color: C.cyan, align: 'center', weight: 900, alpha: fadeIn(t, S.year + 0.5, 0.2), stroke: OUT, sw: 6 });
  // あなたの 1 年ぶん
  const g = ease.out(seg(t, S.yearNum - 0.1, 0.7)), xe = X(71.6 * g);
  ctx.save(); ctx.shadowColor = C.yellow; ctx.shadowBlur = 20; lineSeg(x0, y, xe, y, C.yellow, 14, fadeIn(t, S.yearNum - 0.1, 0.05)); ctx.restore();
  circle(xe, y, 14, '#fff', fadeIn(t, S.yearNum - 0.1, 0.05), '#fff', 24);
  const nA = fadeIn(t, S.yearNum - 0.05), nP = pop(t, S.yearNum - 0.05);
  ctx.save(); ctx.globalAlpha *= nA; ctx.translate(1010, 772); ctx.scale(nP, nP);
  const wk = measure('km', 50, F.num, 400), wo = measure('億', 70, F.jp, 900), wn = measure('72', 132, F.num, 400), wp = measure('約', 44, F.jp, 900);
  text('km', 0, 0, { size: 50, family: F.num, weight: 400, color: C.yellow, align: 'right', stroke: OUT, sw: 8 });
  text('億', -wk - 8, 0, { size: 70, color: C.yellow, align: 'right', stroke: OUT, sw: 10 });
  text('72', -wk - wo - 16, 4, { size: 132, family: F.num, weight: 400, color: C.yellow, align: 'right', stroke: OUT, sw: 12, glow: C.yellow });
  text('約', -wk - wo - wn - 28, 0, { size: 44, color: C.ink, align: 'right', stroke: OUT, sw: 9 });
  ctx.restore();
  text('海王星までの 約1.6倍', X(71.6) + 20, y + 92, { size: 30, color: C.yellow, align: 'right', weight: 900, alpha: fadeIn(t, S.yearNum + 0.5, 0.2), stroke: OUT, sw: 7 });
  text('秒速およそ227km × 1年（銀河の中心に対して）', 70, 700, { size: 22, color: C.ink3, weight: 700, alpha: nA });
  ctx.restore();
}

// ---------------------------------------------------------------- 同じ場所にいたことがない
function sceneNever(t) {
  const a = inOut(t, S.never - 0.05, S.goal - 0.05, 0.3, 0.25);
  if (a <= 0) return;
  drawGalaxy(540, 860, 430, 1.4 + (t - S.never) * 0.04, { tilt: 1, ang: 0, alpha: a * 0.3, bright: 0.9 });   // 2 億年の 1 周の、ほんの一部
  ctx.save(); ctx.globalAlpha *= a;
  const y = 880, xr = 880, k = ease.out(seg(t, S.never, 0.8));
  // あなたが通ってきた 1 本の線(同じ場所を二度と通らない)
  ctx.save(); ctx.shadowColor = C.yellow; ctx.shadowBlur = 30;
  ctx.strokeStyle = grad(40, 0, xr, 0, [[0, 'rgba(255,225,74,0)'], [0.3, 'rgba(255,225,74,0.75)'], [1, '#FFF3B0']]); ctx.lineWidth = 14; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(xr - (xr - 30) * k, y); ctx.lineTo(xr, y); ctx.stroke(); ctx.restore();
  [['10年前', '約720億km'], ['20年前', '約1,440億km'], ['30年前', '約2,160億km']].forEach(([age, dist], i) => {
    const x = xr - (i + 1) * 240, t0 = S.never + 0.45 + i * 0.4, pa = fadeIn(t, t0, 0.15), pk = pop(t, t0);
    pin(x, y, 26 * pk, C.cyan, pa * 0.6);
    text(age, x, y - 78, { size: 46, color: C.cyan, align: 'center', alpha: pa, stroke: OUT, sw: 9 });
    text(dist, x, y + 58, { size: 29, color: C.ink, align: 'center', weight: 900, alpha: pa, stroke: OUT, sw: 7 });
  });
  const ph = (t * 1.1) % 1;
  ring(xr, y, 14 + 44 * ph, C.red, 3, 1 - ph);
  pin(xr, y, 42, C.red, 1);
  text('いまのあなた', xr + 10, y - 112, { size: 34, color: C.ink, align: 'center', weight: 900, stroke: OUT, sw: 8 });
  const wA = fadeIn(t, S.neverWord + 0.45), wP = pop(t, S.neverWord + 0.45);      // 声より先に結論を出さない
  ctx.save(); ctx.globalAlpha *= wA; ctx.translate(540, 690); ctx.scale(wP, wP);
  const w1 = measure('同じ場所は ', 60), w2 = measure('一度もない', 68);
  text('同じ場所は ', -(w1 + w2) / 2, 0, { size: 60, color: C.ink, stroke: OUT, sw: 11 });
  text('一度もない', -(w1 + w2) / 2 + w1, 2, { size: 68, color: C.yellow, stroke: OUT, sw: 12, glow: C.yellow });
  ctx.restore();
  text('※銀河の中心から見た位置。1年に約72億kmずつ うしろへ離れていく', 540, 1002, { size: 23, color: C.ink3, align: 'center', weight: 700, alpha: fadeIn(t, S.never + 0.6, 0.3) });
  ctx.restore();
}
// 年齢 × 72億km(コメントのきっかけ。読み上げはしない)。通過ログの位置に出す
function agePromptAlpha(t) { return inOut(t, S.yearNum + 0.5, S.goal - 0.2, 0.25, 0.25); }
function drawAgePrompt(t) {
  const a = agePromptAlpha(t);
  if (a <= 0) return;
  text('コメントで教えて', 480, 1296, { size: 26, color: C.yellow, align: 'center', weight: 900, alpha: a });
  pillLabel(480, 1356, 'あなたの年齢 × 約72億km ＝ ？', { size: 40, alpha: a, k: ease.back(seg(t, S.yearNum + 0.5, 0.3)), line: C.yellow, icon: false });
}

// ---------------------------------------------------------------- ゴール: 見始めた場所は、ほぼ地球 1 個ぶん後ろ
function sceneGoal(t) {
  const a = fadeIn(t, S.goal - 0.05, 0.3);
  if (a <= 0) return;
  const D = V_GAL * t, p = clamp(D / EARTH_D), r = 140, ex = 770, ey = 752, done = t >= S.payoff;
  const gx = ex + BACK[0] * 2 * r * p, gy = ey + BACK[1] * 2 * r * p;       // 見始めたときに地球があった位置(同じ縮尺)
  const land = seg(t, PLAN.GOAL_T - 0.3, 0.3);
  ctx.save(); ctx.globalAlpha *= a;
  lineSeg(gx, gy, ex, ey, 'rgba(255,255,255,0.85)', 4, 1, [3, 9]);          // 2 点を結ぶ線(= メーターの距離)
  if (!done) {
    // 答えはまだ見せない: 「いま」と「見始めた場所」の 2 点と、残りの距離だけ
    const ph = (t * 1.2) % 1;
    ring(gx, gy, 12 + 40 * ph, C.cyan, 3, 1 - ph);
    circle(gx, gy, 13, C.cyan, 1, C.cyan, 20);
    text('見始めた場所', gx, gy + 62, { size: 36, color: C.cyan, align: 'center', weight: 900, stroke: OUT, sw: 8 });
    pin(ex, ey, 36, C.red, 1);
    text('いま', ex + 34, ey - 50, { size: 40, color: C.ink, weight: 900, stroke: OUT, sw: 8 });
    text('ゴールまで あと', 70, 650, { size: 36, color: C.ink2, weight: 900, stroke: OUT, sw: 8 });
    bigNum(70, 752, '', fmtInt(Math.max(0, EARTH_D - D)), 'km', C.yellow, { size: 100 });
  } else {
    // 「ほぼ地球 1 個ぶん」: 2 つの地球が現れ、すき間が閉じていく
    const pk = ease.back(seg(t, S.payoff, 0.32)), rr1 = r * (0.3 + 0.7 * pk);
    ctx.save(); ctx.globalAlpha *= 0.6; drawGlobe(gx, gy, rr1, 138, 26, 1, 0); ctx.restore();
    ring(gx, gy, rr1, C.cyan, 5 + 4 * land, 1, [12, 10]);
    drawGlobe(ex, ey, rr1, 138, 26, 1, 1 + land);
    const pj = Globe.project(35.68, 139.77, 138, 26, rr1);
    pin(ex + pj.x, ey + pj.y, 20, C.red, 1);
    circle(gx, gy, 7, C.cyan); circle(ex, ey, 7, '#fff');
    text('見始めた', gx - r - 14, gy - 4, { size: 34, color: C.cyan, align: 'right', weight: 900, stroke: OUT, sw: 8 });
    text('場所', gx - r - 14, gy + 38, { size: 34, color: C.cyan, align: 'right', weight: 900, stroke: OUT, sw: 8 });
    text('いま', ex + r + 12, ey + 12, { size: 36, color: C.ink, weight: 900, stroke: OUT, sw: 8 });
    if (t >= S.behind - 0.05) {                   // 「うしろ」
      const ba = fadeIn(t, S.behind - 0.05), ang = Math.atan2(gy - ey, gx - ex);
      ctx.save(); ctx.globalAlpha *= ba; ctx.translate(gx - BACK[0] * 24, gy - BACK[1] * 24); ctx.rotate(ang); ctx.fillStyle = '#fff';
      ctx.beginPath(); ctx.moveTo(26, 0); ctx.lineTo(-12, -18); ctx.lineTo(-12, 18); ctx.closePath(); ctx.fill(); ctx.restore();
    }
    // メーターが向かっている数字
    const tk = pop(t, S.payoff, 0.3);
    text('離れた距離', 70, 640, { size: 34, color: C.ink2, weight: 900, stroke: OUT, sw: 8 });
    text('≒ 地球の直径', 70, 694, { size: 46 * tk, color: C.yellow, stroke: OUT, sw: 10, glow: C.yellow });
    bigNum(70, 782, '', '12,742', 'km', C.yellow, { size: 88, pop: 1 + 0.08 * land });
    text('（平均）※銀河を回るぶん・およそ', 70, 818, { size: 21, color: C.ink3, weight: 700, stroke: OUT, sw: 5 });
    if (land > 0) { ring(ex, ey, r + 6 + 34 * land, '#fff', 5, land); ring(gx, gy, r + 6 + 34 * land, '#fff', 5, land); }
  }
  ctx.restore();
}

// ---------------------------------------------------------------- 通過ログ・クレジット
function drawMilestones(t) {
  const fade = fadeIn(t, S.who + 0.6, 0.4) * (1 - agePromptAlpha(t));
  if (fade <= 0) return;
  const passed = PLAN.milestones.filter(m => t >= m.t && !m.quiet);
  if (!passed.length) return;
  const d = t - passed[passed.length - 1].t, slide = ease.out(seg(d, 0, 0.3));
  text('通過ログ', 480, 1296, { size: 24, color: C.ink3, align: 'center', weight: 900, alpha: fade * 0.9 });
  for (let j = 0; j < Math.min(2, passed.length); j++) {
    const m = passed[passed.length - 1 - j], str = `${m.label} 約${fmtInt(m.km)}km`;
    if (j === 0) pillLabel(480, 1352, str + ' 通過', { size: 36, alpha: fade * fadeIn(d, 0, 0.1), k: ease.back(seg(d, 0, 0.25)), line: m.planet ? C.yellow : (d < 1.2 ? C.cyan : 'rgba(61,224,255,0.45)') });
    else text('✓ ' + str, 480, 1352 + slide * 56 + 13, { size: 29, color: C.ink2, align: 'center', weight: 700, alpha: fade * 0.62 * slide });
  }
}
function drawCredit(t) {
  // 冒頭(メーターが中央にある間)は出さない。以降は最後まで表示
  text('音声 VOICEVOX:青山龍星 ｜ 出典 国立天文台 VERA（2020）・NASA ｜ 都市間は地表の最短距離', 480, 1484,
    { size: 22, color: C.ink3, align: 'center', weight: 500, alpha: 0.8 * seg(t, S.who + 0.9, 0.4), maxW: 820 });
}

// ---------------------------------------------------------------- メイン
window.render = (t) => {
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.filter = 'none';
  drawBackground(t, SPEED_KEYS, seg(t, S.galaxy, 1) * (1 - seg(t, S.tease, 1)) * 0.6);
  const [sx, sy] = shakeAt(t);
  ctx.save(); ctx.translate(sx, sy);
  drawDome(t);
  const gb = galaxyBackdrop(t);
  sceneLap(t);
  drawVignette();
  sceneHook(t, headerState(t));
  sceneSuspects(t);
  sceneSpin(t);
  sceneVerdict(t, 0, S.spinV, S.orbit, S.spinLane + 0.5);
  sceneOrbit(t);
  sceneVerdict(t, 1, S.orbitV, S.zoom, S.orbitLane + 0.5);
  sceneZoomOut(t);
  sceneGalaxy(t, gb);
  sceneVerdict(t, 2, S.galaxyV, S.tease, S.match);
  sceneTease(t);
  sceneParker(t);
  sceneYear(t);
  sceneNever(t);
  sceneGoal(t);
  drawHeader(t);
  ctx.restore();
  drawMilestones(t);
  drawAgePrompt(t);
  drawCredit(t);
  const f = flashAt(t);
  if (f > 0) { ctx.fillStyle = `rgba(255,255,255,${f})`; ctx.fillRect(0, 0, W, H); }
  drawTelop(t, TL);
};

// サムネイル用の 1 枚(冒頭の構図に大きい見出しを重ねる)
window.renderPoster = () => {
  const t = 2.4;                                 // 百の位が「5」で止まって見える瞬間
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  drawBackground(t, SPEED_KEYS, 0);
  drawDome(t);
  drawVignette();
  sceneHook(t, 1, false);
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
