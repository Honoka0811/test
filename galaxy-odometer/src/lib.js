// 共通ユーティリティ(描画は全部 Canvas 2D。render(t) は時刻 t 秒のフレームを決定論的に描く)
const W = 1080, H = 1920;
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');

const F = {
  jp: '"Noto Sans JP"',      // テロップ・ラベル
  num: '"Anton"',            // メーター・大きい数字
};
const C = {
  bg0: '#03061a', bg1: '#0a1338', bg2: '#101c52',
  ink: '#ffffff', ink2: '#b9c4e6', ink3: '#7f8bb5', line: 'rgba(160,180,255,0.22)',
  yellow: '#FFE14A', yellowDeep: '#FFB800', cyan: '#3DE0FF', orange: '#FF9F43', pink: '#FF5FA8',
  red: '#FF4B4B', green: '#4BE38A', panel: 'rgba(10,18,56,0.78)', panelLine: 'rgba(120,150,255,0.35)',
};

const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const seg = (t, s, d) => clamp((t - s) / d);                 // s から d 秒かけて 0→1
const ease = {
  out: t => 1 - Math.pow(1 - clamp(t), 3),
  out5: t => 1 - Math.pow(1 - clamp(t), 5),
  in: t => Math.pow(clamp(t), 3),
  inOut: t => { t = clamp(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; },
  back: t => { t = clamp(t); const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  elastic: t => { t = clamp(t); if (t === 0 || t === 1) return t; return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI) / 3) + 1; },
};
// 出現→保持→退場の不透明度
const inOut = (t, t0, t1, fin = 0.25, fout = 0.25) => Math.min(seg(t, t0, fin), 1 - seg(t, t1 - fout, fout));

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const fmtInt = n => Math.floor(n).toLocaleString('en-US');

function font(size, family = F.jp, weight = 900) { return `${weight} ${size}px ${family}`; }

// 縁取りつきテキスト。opts: size, family, weight, color, align, base, alpha, stroke(色), sw(縁の太さ), glow(色), glowBlur, ls
function text(str, x, y, o = {}) {
  const { size = 48, family = F.jp, weight = 900, color = C.ink, align = 'left', base = 'alphabetic', alpha = 1,
    stroke = null, sw = 0, glow = null, glowBlur = 24, ls = 0, maxW = 0 } = o;
  if (alpha <= 0) return 0;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.font = font(size, family, weight);
  ctx.textAlign = align; ctx.textBaseline = base;
  if (ls) ctx.letterSpacing = ls + 'px';
  let sx = 1;
  const w = ctx.measureText(str).width;
  if (maxW && w > maxW) { sx = maxW / w; ctx.translate(x, y); ctx.scale(sx, 1); x = 0; y = 0; }
  if (stroke && sw) {
    ctx.lineJoin = 'round'; ctx.miterLimit = 2; ctx.strokeStyle = stroke; ctx.lineWidth = sw;
    ctx.strokeText(str, x, y);
  }
  if (glow) { ctx.shadowColor = glow; ctx.shadowBlur = glowBlur; }
  ctx.fillStyle = color;
  ctx.fillText(str, x, y);
  ctx.restore();
  return w * sx;
}
function measure(str, size, family = F.jp, weight = 900, ls = 0) {
  ctx.save(); ctx.font = font(size, family, weight); if (ls) ctx.letterSpacing = ls + 'px';
  const w = ctx.measureText(str).width; ctx.restore(); return w;
}

function rr(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function panel(x, y, w, h, r = 22, alpha = 1, fill = C.panel, line = C.panelLine, lw = 2) {
  if (alpha <= 0 || w <= 0 || h <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha;
  rr(x, y, w, h, r); ctx.fillStyle = fill; ctx.fill();
  if (line) { ctx.strokeStyle = line; ctx.lineWidth = lw; ctx.stroke(); }
  ctx.restore();
}
function bar(x, y, w, h, r, fill, alpha = 1, glow = null) {
  if (alpha <= 0 || w <= 0 || h <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha;
  if (glow) { ctx.shadowColor = glow; ctx.shadowBlur = 22; }
  rr(x, y, w, h, r); ctx.fillStyle = fill; ctx.fill(); ctx.restore();
}
function circle(x, y, r, fill, alpha = 1, glow = null, blur = 20) {
  if (alpha <= 0 || r <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha;
  if (glow) { ctx.shadowColor = glow; ctx.shadowBlur = blur; }
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fillStyle = fill; ctx.fill(); ctx.restore();
}
function ring(x, y, r, color, lw = 3, alpha = 1, dash = null) {
  if (alpha <= 0 || r <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = lw;
  if (dash) ctx.setLineDash(dash);
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
}
function lineSeg(x1, y1, x2, y2, color, lw = 2, alpha = 1, dash = null) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round';
  if (dash) ctx.setLineDash(dash);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.restore();
}
function grad(x0, y0, x1, y1, stops) {
  const g = ctx.createLinearGradient(x0, y0, x1, y1);
  stops.forEach(([p, c]) => g.addColorStop(p, c));
  return g;
}
function rgrad(x, y, r0, r1, stops) {
  const g = ctx.createRadialGradient(x, y, r0, x, y, r1);
  stops.forEach(([p, c]) => g.addColorStop(p, c));
  return g;
}
function glowBlob(x, y, r, color, alpha = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.globalCompositeOperation = 'lighter';
  ctx.fillStyle = rgrad(x, y, 0, r, [[0, color], [1, 'rgba(0,0,0,0)']]);
  ctx.fillRect(x - r, y - r, r * 2, r * 2); ctx.restore();
}
// 〇/×/✓ をコードで描く
function markCross(x, y, s, color, lw = 8, alpha = 1, p = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round';
  const a = clamp(p * 2), b = clamp(p * 2 - 1);
  ctx.beginPath(); ctx.moveTo(x - s, y - s); ctx.lineTo(x - s + 2 * s * a, y - s + 2 * s * a); ctx.stroke();
  if (b > 0) { ctx.beginPath(); ctx.moveTo(x + s, y - s); ctx.lineTo(x + s - 2 * s * b, y - s + 2 * s * b); ctx.stroke(); }
  ctx.restore();
}
function markCheck(x, y, s, color, lw = 8, alpha = 1, p = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const a = clamp(p * 2.5), b = clamp((p - 0.4) / 0.6);
  ctx.beginPath(); ctx.moveTo(x - s, y); ctx.lineTo(x - s + s * 0.7 * a, y + s * 0.7 * a);
  if (b > 0) ctx.lineTo(x - s * 0.3 + s * 1.4 * b, y + s * 0.7 - s * 1.5 * b);
  ctx.stroke(); ctx.restore();
}
// 位置ピン
function pin(x, y, s, color, alpha = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(x, y - s * 1.4, s * 0.8, Math.PI * 0.85, Math.PI * 0.15, false);
  ctx.lineTo(x, y); ctx.closePath(); ctx.fill();
  ctx.fillStyle = C.bg0; ctx.beginPath(); ctx.arc(x, y - s * 1.45, s * 0.3, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}
