// 画面部品: 背景の星、実走メーター、ゴールゲージ、テロップ、地球儀、銀河

// ---------------------------------------------------------------- 背景
const STARS = (() => {
  const r = mulberry32(7), a = [];
  for (let i = 0; i < 170; i++) a.push({ x: r() * 1400, y: r() * 2300, z: 0.25 + r() * r() * 0.95, tw: r() * 6.28, hue: r() });
  return a;
})();
const STAR_DIR = (() => { const a = Math.atan2(0.86, -0.5); return [Math.cos(a), Math.sin(a)]; })(); // 右上→左下へ流れる

// 速度キー [[t, v], ...] を積分して「流れた量」を返す
function integrateKeys(keys, t) {
  let s = 0;
  for (let i = 0; i < keys.length - 1; i++) {
    const [t0, v0] = keys[i], [t1, v1] = keys[i + 1];
    if (t <= t0) break;
    const tt = Math.min(t, t1), k = (tt - t0) / (t1 - t0 || 1), v = v0 + (v1 - v0) * k;
    s += (v0 + v) / 2 * (tt - t0);
  }
  const last = keys[keys.length - 1];
  if (t > last[0]) s += last[1] * (t - last[0]);
  return s;
}
function valueKeys(keys, t) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [t0, v0] = keys[i], [t1, v1] = keys[i + 1];
    if (t <= t1) return v0 + (v1 - v0) * ((t - t0) / (t1 - t0 || 1));
  }
  return keys[keys.length - 1][1];
}

function drawBackground(t, speedKeys, tint = 0) {
  ctx.fillStyle = grad(0, 0, 0, H, [[0, C.bg0], [0.55, C.bg1], [1, '#070b26']]);
  ctx.fillRect(0, 0, W, H);
  // ゆっくり動く星雲
  glowBlob(240 + 60 * Math.sin(t * 0.11), 520 + 40 * Math.cos(t * 0.09), 620, 'rgba(60,70,220,0.28)');
  glowBlob(900 + 50 * Math.cos(t * 0.07), 1350 + 60 * Math.sin(t * 0.1), 700, 'rgba(150,50,200,0.20)');
  if (tint > 0) glowBlob(540, 860, 900, 'rgba(255,200,60,0.10)', tint);
  const S = integrateKeys(speedKeys, t), v = valueKeys(speedKeys, t);
  ctx.save(); ctx.lineCap = 'round';
  for (const s of STARS) {
    const k = s.z;
    let x = (s.x + STAR_DIR[0] * S * k) % 1400; if (x < 0) x += 1400;
    let y = (s.y + STAR_DIR[1] * S * k) % 2300; if (y < 0) y += 2300;
    x -= 160; y -= 190;
    const len = Math.max(0, v * k * 0.055);
    const a = (0.35 + 0.65 * k) * (0.75 + 0.25 * Math.sin(s.tw + t * 2.3));
    ctx.globalAlpha = Math.min(1, a);
    const col = s.hue < 0.15 ? '#ffd9a8' : s.hue < 0.4 ? '#a8c8ff' : '#ffffff';
    if (len < 2.5) {
      ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, 0.9 + k * 1.5, 0, 6.2832); ctx.fill();
    } else {
      const g = ctx.createLinearGradient(x, y, x - STAR_DIR[0] * len, y - STAR_DIR[1] * len);
      g.addColorStop(0, col); g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.strokeStyle = g; ctx.lineWidth = 1.2 + k * 2.2;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - STAR_DIR[0] * len, y - STAR_DIR[1] * len); ctx.stroke();
    }
  }
  ctx.restore();
}
function drawVignette() {
  ctx.fillStyle = rgrad(540, 900, 520, 1250, [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,8,0.62)']]);
  ctx.fillRect(0, 0, W, H);
}

// ---------------------------------------------------------------- 実走メーター
// D(t) = 227 km/s × 動画の経過秒。どのフレームでも実際の値。
const V_GAL = 227, V_ORB = 29.78, V_SPIN = 0.378, EARTH_D = 12742;
const GOAL_T = EARTH_D / V_GAL;                 // 56.13 秒
const DIGIT_T = [0, 10 / V_GAL, 100 / V_GAL, 1000 / V_GAL, 10000 / V_GAL]; // 桁が増える時刻
let _odo = null;
function odoMetrics() {
  if (_odo) return _odo;
  ctx.save(); ctx.font = font(100, F.num, 400);
  let w = 0, asc = 0;
  for (let d = 0; d < 10; d++) { const m = ctx.measureText(String(d)); w = Math.max(w, m.width); asc = Math.max(asc, m.actualBoundingBoxAscent); }
  const comma = ctx.measureText(',').width;
  ctx.restore();
  return (_odo = { cw: w / 100 * 1.07, asc: asc / 100, comma: comma / 100 * 1.15 });
}
// cx, cy: 数字ブロックの中心。size: フォントサイズ。t: 動画時刻(桁増えアニメとブラー用)
const ROLL_SEC = [0, 0, 0.16, 0.26, 0.30];      // 百の位以上が 1 つ進むのにかける秒数
function drawOdometer(t, cx, cy, size, o = {}) {
  const { alpha = 1, unit = true, color0 = '#FFF6A8', color1 = '#FFC400', glow = 1, panelA = 1, pulse = 0 } = o;
  if (alpha <= 0) return { left: cx, right: cx, w: 0 };
  const m = odoMetrics(), cw = m.cw * size, asc = m.asc * size, cmw = m.comma * size;
  // 桁数(増える瞬間に 0.22 秒かけて幅を広げる)
  let nd = 1;
  for (let p = 1; p < 5; p++) nd += ease.out(seg(t, DIGIT_T[p], 0.22));
  const ndInt = Math.ceil(nd - 1e-6);
  const commaK = ease.out(seg(t, DIGIT_T[3], 0.22));
  const unitSize = size * 0.40, unitGap = size * 0.10, unitW = unit ? measure('km', unitSize, F.num, 400) + unitGap : 0;
  const total = nd * cw + commaK * cmw + unitW;
  const right = cx + total / 2 - unitW;          // 一の位の右端
  const pitch = asc * 1.30, hh = asc * 1.36, top = cy - hh / 2;
  const padX = size * 0.16, px0 = cx - total / 2 - padX, pw = total + padX * 2, ph = hh + size * 0.06, py0 = cy - ph / 2;
  ctx.save();
  ctx.globalAlpha *= alpha;
  if (glow > 0) glowBlob(cx, cy, size * 2.0, 'rgba(255,200,40,0.15)', glow * (1 + pulse));
  // 計器の窓
  if (panelA > 0) {
    ctx.save(); ctx.globalAlpha *= panelA;
    rr(px0, py0, pw, ph, size * 0.12); ctx.fillStyle = 'rgba(3,6,24,0.82)'; ctx.fill();
    ctx.strokeStyle = `rgba(255,210,70,${0.55 + 0.45 * pulse})`; ctx.lineWidth = Math.max(2, size * 0.014); ctx.stroke();
    ctx.restore();
  }
  ctx.save();
  rr(px0, py0, pw, ph, size * 0.12); ctx.clip();
  ctx.font = font(size, F.num, 400); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.lineJoin = 'round';
  const fill = grad(0, cy - asc / 2, 0, cy + asc / 2, [[0, color0], [1, color1]]);
  const by = cy + asc / 2;
  const drawCol = (p, tt, a, soft = false) => {
    const pw10 = Math.pow(10, p), v = V_GAL * tt / pw10;
    const d = Math.floor(v) % 10, f = v - Math.floor(v);
    let off = f;                                  // 一・十の位は連続回転
    if (p >= 2) { const period = pw10 / V_GAL, k = Math.min(1, ROLL_SEC[p] / period); off = ease.inOut(clamp((f - (1 - k)) / k)); }
    const x = right - (p + 0.5) * cw - (p >= 3 ? commaK * cmw : 0);
    const appear = p === 0 ? 1 : ease.out(seg(t, DIGIT_T[p], 0.22));
    if (appear <= 0) return;
    ctx.save();
    ctx.globalAlpha *= a * appear;
    for (let k = 0; k < 2; k++) {
      if (p > 0 && Math.floor(v) + k === 0) continue;   // 先頭桁の 0 は出さない
      const dig = (d + k) % 10, y = by - off * pitch + k * pitch;
      if (y - asc > top + hh || y < top) continue;
      if (!soft) { ctx.strokeStyle = 'rgba(30,14,0,0.9)'; ctx.lineWidth = size * 0.05; ctx.strokeText(String(dig), x, y); }
      ctx.fillStyle = fill; ctx.fillText(String(dig), x, y);
    }
    ctx.restore();
  };
  for (let p = ndInt - 1; p >= 0; p--) {
    if (p <= 1) {                                 // 速すぎる桁は 1 フレームぶんの動きを細かく重ねてモーションブラーにする
      const K = 20;
      for (let k = 0; k < K; k++) drawCol(p, Math.max(0, t - k / (60 * K)), p === 0 ? 0.10 : 0.15, true);
    } else drawCol(p, t, 1);
  }
  if (commaK > 0) {
    ctx.save(); ctx.globalAlpha *= commaK;
    const x = right - 3 * cw - cmw / 2 * commaK;
    ctx.strokeStyle = 'rgba(30,14,0,0.9)'; ctx.lineWidth = size * 0.05; ctx.strokeText(',', x, by);
    ctx.fillStyle = fill; ctx.fillText(',', x, by);
    ctx.restore();
  }
  if (unit) {
    ctx.font = font(unitSize, F.num, 400); ctx.textAlign = 'left';
    ctx.strokeStyle = 'rgba(30,14,0,0.9)'; ctx.lineWidth = size * 0.035; ctx.strokeText('km', right + unitGap, by);
    ctx.fillStyle = fill; ctx.fillText('km', right + unitGap, by);
  }
  // 回転ドラムの陰影(上下を暗く)
  ctx.fillStyle = grad(0, py0, 0, py0 + ph, [[0, 'rgba(3,6,24,0.95)'], [0.2, 'rgba(3,6,24,0)'], [0.8, 'rgba(3,6,24,0)'], [1, 'rgba(3,6,24,0.95)']]);
  ctx.fillRect(px0, py0, pw, ph);
  ctx.restore();
  ctx.restore();
  return { left: px0, right: px0 + pw, top: py0, bottom: py0 + ph, w: pw, h: ph };
}

// ---------------------------------------------------------------- ゴールゲージ
// x0..x1 のバーが D/12742 で埋まる。label は左上、右上に %。
function drawGauge(t, y, o = {}) {
  const { alpha = 1, label = 'ゴール', goal = '？？？ 1個ぶん', goalColor = C.ink, x0 = 70, x1 = 1010, pulse = 0, ticks = [] } = o;
  if (alpha <= 0) return;
  const p = clamp(V_GAL * t / EARTH_D), h = 26, w = x1 - x0;
  ctx.save(); ctx.globalAlpha *= alpha;
  text(label, x0, y - 16, { size: 32, color: C.ink2, weight: 900 });
  const lw = measure(label, 32, F.jp, 900);
  text(goal, x0 + lw + 16, y - 16, { size: 38, color: goalColor, weight: 900 });
  text(Math.floor(p * 100) + '%', x1, y - 14, { size: 40, family: F.num, weight: 400, color: C.yellow, align: 'right' });
  bar(x0, y, w, h, h / 2, 'rgba(255,255,255,0.10)');
  ctx.save(); rr(x0, y, w, h, h / 2); ctx.strokeStyle = 'rgba(255,255,255,0.28)'; ctx.lineWidth = 2; ctx.stroke(); ctx.restore();
  for (const tk of ticks) {                       // 通過点の目盛り
    const tx = x0 + w * clamp(tk.km / EARTH_D), passed = V_GAL * t >= tk.km;
    lineSeg(tx, y - 5, tx, y + h + 5, passed ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.35)', 2);
  }
  const fw = Math.max(h, w * p);
  bar(x0, y, fw, h, h / 2, grad(x0, 0, x0 + fw, 0, [[0, '#FF8A00'], [1, C.yellow]]), 1, 'rgba(255,200,40,0.8)');
  const hx = x0 + fw - h / 2;
  circle(hx, y + h / 2, 9 + 5 * pulse, '#fff', 1, '#fff', 18 + 20 * pulse);
  ctx.restore();
}

// ---------------------------------------------------------------- テロップ
// 1 フレーズずつ表示。em のフレーズは黄色、数字は大きく。x 70..890(Shorts の UI を避ける安全域)に収める。
const TELOP = { cx: 480, y: 1206, size: 92, maxW: 820 };
function drawTelopChunk(str, em, age, o = {}) {
  const { cx = TELOP.cx, y = TELOP.y, size = TELOP.size, maxW = TELOP.maxW, alpha = 1 } = o;
  str = str.replace(/[、。]+$/u, '');
  if (!str || alpha <= 0) return;
  const runs = str.split(/([0-9][0-9,\.]*)/).filter(s => s !== '').map(s => {
    const num = /^[0-9]/.test(s);
    return { s, num, size: num ? size * (em ? 1.42 : 1.18) : size, family: num ? F.num : F.jp, weight: num ? 400 : 900 };
  });
  let w = 0;
  for (const r of runs) { r.w = measure(r.s, r.size, r.family, r.weight) + (r.num ? size * 0.06 : 0); w += r.w; }
  const k = Math.min(1, maxW / w);
  const pop = 0.86 + 0.14 * ease.back(seg(age, 0, 0.14)), a = seg(age, 0, 0.07) * alpha;
  ctx.save();
  ctx.translate(cx, y); ctx.scale(k * pop, k * pop); ctx.globalAlpha *= a;
  ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left'; ctx.lineJoin = 'round';
  const pass = (fn) => { let x = -w / 2; for (const r of runs) { ctx.font = font(r.size, r.family, r.weight); fn(r, x + (r.num ? size * 0.03 : 0)); x += r.w; } };
  pass((r, x) => { ctx.strokeStyle = 'rgba(0,0,0,0.55)'; ctx.lineWidth = size * 0.30; ctx.strokeText(r.s, x, 8); });   // 影
  pass((r, x) => { ctx.strokeStyle = '#05070f'; ctx.lineWidth = size * 0.21; ctx.strokeText(r.s, x, 0); });            // 縁
  pass((r, x) => {
    ctx.fillStyle = em ? grad(0, -size, 0, 0, [[0, '#FFF6A8'], [1, C.yellowDeep]]) : '#ffffff';
    ctx.fillText(r.s, x, 0);
  });
  ctx.restore();
}
function drawTelop(t, TL) {
  for (const line of TL.lines) {
    if (t < line.start - 0.05 || t > line.end + 0.5) continue;
    const ch = line.chunks;
    for (let i = 0; i < ch.length; i++) {
      const t0 = ch[i].t0 - 0.04, t1 = i + 1 < ch.length ? ch[i + 1].t0 - 0.04 : line.end + 0.28;
      if (t >= t0 && t < t1) {
        const out = i + 1 < ch.length ? 1 : 1 - seg(t, t1 - 0.12, 0.12);
        drawTelopChunk(ch[i].show, !!ch[i].em, t - t0, { alpha: out });
        return;
      }
    }
  }
}

// ---------------------------------------------------------------- 地球儀(Natural Earth の陸地マスクを正射図法で描く)
const Globe = {
  mask: null, mw: 0, mh: 0, cache: new Map(),
  load() {
    return new Promise((res, rej) => {
      const img = new Image();
      img.onload = () => {
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const g = c.getContext('2d'); g.drawImage(img, 0, 0);
        const d = g.getImageData(0, 0, c.width, c.height).data;
        this.mw = c.width; this.mh = c.height; this.mask = new Uint8Array(c.width * c.height);
        for (let i = 0; i < this.mask.length; i++) this.mask[i] = d[i * 4];
        res();
      };
      img.onerror = rej; img.src = window.LAND_PNG;
    });
  },
  // lon0, lat0: 球の正面に来る経度・緯度(度)。r: 半径 px。戻り値: オフスクリーン canvas(一辺 2r+2)
  render(lon0, lat0, r) {
    r = Math.round(r);
    return this.renderRect(lon0, lat0, r, r + 1, r + 1, r * 2 + 2, r * 2 + 2);
  },
  // 球の中心を canvas 内の (ox, oy) に置き、w×h の範囲だけ描く(大きな球の一部を切り出す用)
  renderRect(lon0, lat0, r, ox, oy, w, h) {
    const key = w + 'x' + h;
    let ent = this.cache.get(key);
    if (!ent) { const c = document.createElement('canvas'); c.width = w; c.height = h; ent = { c, g: c.getContext('2d') }; ent.img = ent.g.createImageData(w, h); this.cache.set(key, ent); }
    const out = ent.img.data, mask = this.mask, mw = this.mw, mh = this.mh;
    const sl = Math.sin(lat0 * Math.PI / 180), cl = Math.cos(lat0 * Math.PI / 180), l0 = lon0 * Math.PI / 180;
    const Lx = -0.46, Ly = 0.42, Lz = 0.78;         // 光源(左上手前)
    const TWO_PI = Math.PI * 2, GR = Math.PI / 6;   // 30°ごとの経緯線
    for (let py = 0; py < h; py++) {
      const y = (oy - 0.5 - py) / r;
      for (let px = 0; px < w; px++) {
        const x = (px + 0.5 - ox) / r, d2 = x * x + y * y, i = (py * w + px) * 4;
        if (d2 > 1.02) { out[i + 3] = 0; continue; }
        const dd = Math.sqrt(d2), z = Math.sqrt(Math.max(0, 1 - d2));
        const y2 = y * cl + z * sl, z2 = -y * sl + z * cl;
        const lat = Math.asin(clamp(y2, -1, 1)), lon = l0 + Math.atan2(x, z2);
        let u = (lon / TWO_PI + 0.5) % 1; if (u < 0) u += 1;
        const vv = clamp(0.5 - lat / Math.PI, 0, 0.99999);
        // 陸地マスクをバイリニアで読む
        const fx = u * mw - 0.5, fy = vv * mh - 0.5, ix = Math.floor(fx), iy = Math.floor(fy), tx = fx - ix, ty = fy - iy;
        const x0 = (ix + mw) % mw, x1 = (ix + 1) % mw, y0 = Math.max(0, iy), y1 = Math.min(mh - 1, iy + 1);
        const land = ((mask[y0 * mw + x0] * (1 - tx) + mask[y0 * mw + x1] * tx) * (1 - ty) + (mask[y1 * mw + x0] * (1 - tx) + mask[y1 * mw + x1] * tx) * ty) / 255;
        const dif = Math.max(0, x * Lx + y * Ly + z * Lz), lit = 0.30 + 0.70 * dif;
        // 海: 深い青、陸: 明るい緑
        let R = (14 + 20 * dif) * (1 - land) + (70 + 80 * dif) * land;
        let G = (58 + 92 * dif) * (1 - land) + (176 + 62 * dif) * land;
        let B = (150 + 100 * dif) * (1 - land) + (104 + 30 * dif) * land;
        R *= lit; G *= lit; B *= lit;
        // 経緯線
        const gl = Math.abs(((lon % GR) + GR) % GR - GR / 2), ga = Math.abs(((lat % GR) + GR) % GR - GR / 2);
        const wl = 1.6 / (r * Math.max(0.15, Math.cos(lat)) * Math.max(0.2, z)), wa = 1.6 / (r * Math.max(0.2, z));
        const gline = Math.max(clamp(1 - (GR / 2 - gl) / wl), clamp(1 - (GR / 2 - ga) / wa)) * 0.16;
        R += (255 - R) * gline; G += (255 - G) * gline; B += (255 - B) * gline;
        // 大気のふち
        const rim = Math.pow(1 - z, 2.6);
        R += (120 - R) * rim * 0.75; G += (200 - G) * rim * 0.75; B += (255 - B) * rim * 0.75;
        out[i] = R; out[i + 1] = G; out[i + 2] = B; out[i + 3] = 255 * clamp((1 - dd) * r + 0.5);
      }
    }
    ent.g.putImageData(ent.img, 0, 0);
    return ent.c;
  },
  // 地点(lat, lon)の画面上の位置。裏側なら visible=false
  project(lat, lon, lon0, lat0, r) {
    const la = lat * Math.PI / 180, lo = (lon - lon0) * Math.PI / 180, p0 = lat0 * Math.PI / 180;
    const x = Math.cos(la) * Math.sin(lo), yw = Math.sin(la), zw = Math.cos(la) * Math.cos(lo);
    const y = yw * Math.cos(p0) - zw * Math.sin(p0), z = yw * Math.sin(p0) + zw * Math.cos(p0);
    return { x: x * r, y: -y * r, visible: z > 0, z };
  },
};
function drawGlobe(cx, cy, r, lon0, lat0, alpha = 1, glow = 1) {
  if (alpha <= 0 || r < 2) return;
  ctx.save(); ctx.globalAlpha *= alpha;
  if (glow > 0) glowBlob(cx, cy, r * 1.55, 'rgba(70,150,255,0.30)', glow);
  const c = Globe.render(lon0, lat0, r);
  ctx.drawImage(c, Math.round(cx - c.width / 2), Math.round(cy - c.height / 2));
  ctx.restore();
}

// 画面下からのぞく大きな地球。cy は球の中心(画面外)。日本が上端近くに来る向きにしてある。
const DOME = { r: 720, cx: 540, cy: 2170, lon0: 137, lat0: -22 };
function drawEarthDome(alpha = 1, dy = 0) {
  if (alpha <= 0) return null;
  const { r, cx, lon0, lat0 } = DOME, cy = DOME.cy + dy;
  const top = Math.max(0, Math.floor(cy - r - 2)), hgt = H - top;
  if (hgt <= 0) return null;
  ctx.save(); ctx.globalAlpha *= alpha;
  // 大気の光
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  ctx.fillStyle = rgrad(cx, cy, r * 0.97, r * 1.16, [[0, 'rgba(90,170,255,0.55)'], [1, 'rgba(0,0,0,0)']]);
  ctx.fillRect(0, top - 140, W, hgt + 140); ctx.restore();
  const c = Globe.renderRect(lon0, lat0, r, cx, cy - top, W, hgt);
  ctx.drawImage(c, 0, top);
  ctx.restore();
  const p = Globe.project(35.68, 139.77, lon0, lat0, r);
  return { x: cx + p.x, y: cy + p.y };
}

// ---------------------------------------------------------------- 銀河(粒子の渦)
const GALAXY = (() => {
  const rnd = mulberry32(20261114), g = () => { let s = 0; for (let i = 0; i < 4; i++) s += rnd(); return (s - 2) / 0.58; }; // 近似ガウス
  const P = [], B = Math.tan(13.5 * Math.PI / 180), R0 = 0.07;
  for (let i = 0; i < 8200; i++) {
    const k = rnd();
    if (k < 0.24) {                                  // バルジ(中心の棒)
      const rr = Math.abs(g()) * 0.075, th = rnd() * 6.2832;
      P.push({ r: rr, th, e: 1.9, c: 0, s: 1 + rnd() * 1.6, a: 0.35 + rnd() * 0.5 });
    } else if (k < 0.90) {                           // 渦状腕
      const arm = Math.floor(rnd() * 4), major = arm % 2 === 0;
      const rr = R0 + (1 - R0) * Math.pow(rnd(), major ? 0.85 : 1.1) * (major ? 1 : 0.86);
      const th = arm * Math.PI / 2 + Math.log(rr / R0) / B + g() * (0.20 - 0.07 * rr);
      const c = rnd() < 0.07 ? 2 : (rnd() < 0.3 ? 3 : 1);
      P.push({ r: rr + g() * 0.012, th, e: 1, c, s: 0.9 + rnd() * (major ? 2.0 : 1.4), a: (major ? 0.42 : 0.26) + rnd() * 0.45 });
    } else {                                         // 円盤全体に散る星
      const rr = Math.sqrt(rnd()) * 1.02, th = rnd() * 6.2832;
      P.push({ r: rr, th, e: 1, c: 1, s: 0.8 + rnd(), a: 0.12 + rnd() * 0.2 });
    }
  }
  for (let i = 0; i < 1500; i++) {                   // 腕に沿った淡い雲(大きく薄い粒)
    const arm = Math.floor(rnd() * 4), major = arm % 2 === 0;
    const rr = R0 + (1 - R0) * Math.pow(rnd(), 0.9) * (major ? 1 : 0.84);
    const th = arm * Math.PI / 2 + Math.log(rr / R0) / B + g() * 0.13;
    P.push({ r: rr, th, e: 1, c: rnd() < 0.22 ? 5 : 4, s: 7 + rnd() * 13, a: (major ? 0.055 : 0.035) + rnd() * 0.03, round: true });
  }
  const COL = ['#ffe9bd', '#cfe0ff', '#ff86c0', '#ffffff', '#6f8cff', '#ff5fb0'];
  const buckets = COL.map((_, c) => P.filter(p => p.c === c));
  return { P, COL, buckets, sun: { r: 0.52, th: 2.2 } };
})();
// cx, cy 中心、R 半径、rot 回転角、tilt 縦つぶし、ang 全体の傾き。戻り値: 太陽系の画面座標
function drawGalaxy(cx, cy, R, rot, o = {}) {
  const { tilt = 0.52, ang = -0.38, alpha = 1, bright = 1 } = o;
  const ca = Math.cos(ang), sa = Math.sin(ang);
  const P2 = (r, th, e = 1) => {
    const a = th - rot * (0.55 + 0.45 * Math.min(2.2, 0.5 / Math.max(r, 0.12)));  // 内側ほど少し速く回る
    const x = Math.cos(a) * r * R * e, y = Math.sin(a) * r * R * tilt;
    return [cx + x * ca - y * sa, cy + x * sa + y * ca];
  };
  const sunXY = P2(GALAXY.sun.r, GALAXY.sun.th);
  if (alpha <= 0) return sunXY;
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.globalCompositeOperation = 'lighter';
  // 円盤の淡い光と中心核
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang); ctx.scale(1, tilt);
  ctx.fillStyle = rgrad(0, 0, 0, R * 1.05, [[0, `rgba(120,140,255,${0.20 * bright})`], [0.5, `rgba(90,90,220,${0.09 * bright})`], [1, 'rgba(0,0,0,0)']]);
  ctx.fillRect(-R * 1.1, -R * 1.1, R * 2.2, R * 2.2);
  ctx.fillStyle = rgrad(0, 0, 0, R * 0.30, [[0, `rgba(255,236,190,${0.95 * bright})`], [0.25, `rgba(255,200,120,${0.5 * bright})`], [1, 'rgba(0,0,0,0)']]);
  ctx.fillRect(-R * 0.4, -R * 0.4, R * 0.8, R * 0.8);
  ctx.restore();
  GALAXY.buckets.forEach((arr, c) => {
    ctx.fillStyle = GALAXY.COL[c];
    for (const p of arr) {
      const [x, y] = P2(p.r, p.th, p.e);
      ctx.globalAlpha = Math.min(1, p.a * bright) * alpha;
      const s = p.s * (R / 520);
      if (p.round) { ctx.beginPath(); ctx.arc(x, y, s, 0, 6.2832); ctx.fill(); }
      else ctx.fillRect(x - s / 2, y - s / 2, s, s);
    }
  });
  ctx.restore();
  return sunXY;
}
// 太陽系の公転軌道(銀河面上の楕円)
function galaxyOrbitPath(cx, cy, R, o = {}) {
  const { tilt = 0.52, ang = -0.38, r = GALAXY.sun.r } = o;
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang); ctx.scale(1, tilt);
  ctx.beginPath(); ctx.arc(0, 0, r * R, 0, Math.PI * 2); ctx.restore();
}
