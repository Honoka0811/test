// Natural Earth (world-atlas 10m) から東アジア〜西太平洋の陸地を切り出し、map_data.js に書き出す
// 使い方: npm i && node build_map.js
const fs = require('fs');
const path = require('path');
const topojson = require('topojson-client');
const world = require('world-atlas/countries-10m.json');

const BBOX = { w: 96, e: 172, s: -2, n: 58 };     // 経度・緯度の切り出し範囲
const EPS = 0.025;                                 // 間引き: この距離(度)未満の点は捨てる
const MIN_AREA = 0.0008;                           // これより小さい島は捨てる(度^2)。ただし KEEP 対象は残す

// 外地として色を付ける国・地域(現代の国境データを流用)
const TAG = {
  'Japan': 'naichi',
  'South Korea': 'korea', 'North Korea': 'korea',
  'Taiwan': 'taiwan',
  'N. Mariana Is.': 'nanyo', 'Palau': 'nanyo',
};

function area(r) {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] - r[i][0]) * (r[j][1] + r[i][1]);
  return Math.abs(a / 2);
}
function inBox(r) {
  return r.some(([x, y]) => x >= BBOX.w && x <= BBOX.e && y >= BBOX.s && y <= BBOX.n);
}
function simplify(r) {
  const out = [r[0]];
  for (let i = 1; i < r.length; i++) {
    const p = out[out.length - 1];
    if (Math.hypot(r[i][0] - p[0], r[i][1] - p[1]) >= EPS || i === r.length - 1) out.push(r[i]);
  }
  return out.map(([x, y]) => [+x.toFixed(3), +y.toFixed(3)]);
}

const fc = topojson.feature(world, world.objects.countries);
const shapes = [];
for (const f of fc.features) {
  const name = f.properties.name;
  const tag = TAG[name] || 'other';
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polys) {
    const outer = poly[0];
    if (!inBox(outer)) continue;
    const keepSmall = tag === 'nanyo';
    if (!keepSmall && area(outer) < MIN_AREA) continue;
    let t = tag;
    // 樺太(サハリン)を判別し、別タグにする(北緯50度での塗り分けは描画側で行う)
    if (name === 'Russia') {
      const xs = outer.map(p => p[0]), ys = outer.map(p => p[1]);
      if (Math.min(...xs) > 141 && Math.max(...xs) < 145.5 && Math.min(...ys) > 45.5 && Math.max(...ys) < 54.6 && area(outer) > 1) t = 'sakhalin';
    }
    if (name === 'China') t = 'china';
    shapes.push({ t, r: simplify(outer) });
  }
}
const js = '// 自動生成: node build_map.js  (Natural Earth 10m / world-atlas 2.0.2, パブリックドメイン)\nwindow.MAP=' + JSON.stringify(shapes) + ';\n';
fs.writeFileSync(path.join(__dirname, 'map_data.js'), js);
const pts = shapes.reduce((a, s) => a + s.r.length, 0);
console.log(`shapes=${shapes.length} points=${pts} size=${(js.length / 1024).toFixed(0)}KB`,
  'tags', [...new Set(shapes.map(s => s.t))].join(','));
