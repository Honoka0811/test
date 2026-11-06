// Natural Earth(world-atlas, パブリックドメイン)の陸地データを、地図座標に投影して assets/map.js に書き出す
// 使い方: (world-atlas と topojson-client を入れた node_modules があるディレクトリで) node make_map.js
const path = require('path'), fs = require('fs');
const topo = require('topojson-client');
const world = require('world-atlas/land-50m.json');
const MAP = { lon0: 120, lon1: 187, lat0: -12, lat1: 42, w: 1000 };
MAP.kx = MAP.w / (MAP.lon1 - MAP.lon0);
MAP.ky = MAP.kx / Math.cos(15 * Math.PI / 180);   // 正距円筒図法(標準緯線 15°)
MAP.h = Math.round((MAP.lat1 - MAP.lat0) * MAP.ky);
const px = (lon, lat) => [(lon - MAP.lon0) * MAP.kx, (MAP.lat1 - lat) * MAP.ky];
const land = topo.feature(world, world.objects.land);
const rings = [];
const polys = [];
for (const f of (land.features || [land])) { const g = f.geometry; if (g.type === 'MultiPolygon') polys.push(...g.coordinates); else polys.push(g.coordinates); }
for (const poly of polys) for (const ring of poly) {
  // 西半球の陸地はリングごと +360°(日付変更線の東側を 180° 超の経度で扱う)
  const meanLon = ring.reduce((a, p) => a + p[0], 0) / ring.length;
  const r = meanLon < 0 ? ring.map(([lo, la]) => [lo + 360, la]) : ring;
  const lons = r.map(p => p[0]), lats = r.map(p => p[1]);
  if (Math.max(...lons) < MAP.lon0 - 8 || Math.min(...lons) > MAP.lon1 + 8 || Math.max(...lats) < MAP.lat0 - 8 || Math.min(...lats) > MAP.lat1 + 8) continue;
  const out = [];
  for (const [lo, la] of r) { const [x, y] = px(lo, la); out.push(Math.round(x * 2) / 2, Math.round(y * 2) / 2); }
  if (out.length >= 6) rings.push(out);
}
const js = `// make_map.js が生成。陸地データ: Natural Earth 1:50m (public domain) via world-atlas\nwindow.MAP = ${JSON.stringify(MAP)};\nwindow.LAND = ${JSON.stringify(rings)};\n`;
fs.writeFileSync(path.join(__dirname, 'assets', 'map.js'), js);
console.log('rings', rings.length, 'bytes', js.length, 'map', MAP);
