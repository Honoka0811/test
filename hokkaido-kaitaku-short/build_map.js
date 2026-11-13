// Natural Earth(world-atlas, パブリックドメイン)から北海道本島の輪郭を取り出し、map.js に SVG パスとして書き出す
const topo = require('world-atlas/countries-10m.json');
const { feature } = require('topojson-client');
const fs = require('fs');
const jp = feature(topo, topo.objects.countries).features.find(f => f.properties.name === 'Japan');
const W = 1000, LON0 = 139.2, LON1 = 146.0, LAT0 = 41.2, LAT1 = 45.7, K = Math.cos(43.5 * Math.PI / 180);
const S = W / ((LON1 - LON0) * K), H = Math.round((LAT1 - LAT0) * S);
const P = ([lon, lat]) => [((lon - LON0) * K * S), ((LAT1 - lat) * S)];
let d = '';
for (const poly of jp.geometry.coordinates) {
  const ring = poly[0];
  const cx = ring.reduce((a, p) => a + p[0], 0) / ring.length, cy = ring.reduce((a, p) => a + p[1], 0) / ring.length;
  if (cy < 41.3 || cy > 45.8 || cx < 139.2 || cx > 146) continue;
  d += 'M' + ring.map(p => P(p).map(v => v.toFixed(1)).join(',')).join('L') + 'Z';
}
const pt = (lat, lon) => P([lon, lat]).map(v => +v.toFixed(1));
const out = {
  w: W, h: H, path: d,
  sites: { jomon: pt(43.86, 143.60), kusari: pt(43.87, 144.05), shumarinai: pt(44.28, 142.16), abashiri: pt(44.02, 144.27), kitamitoge: pt(43.89, 143.03), sapporo: pt(43.06, 141.35) },
  // 中央道路(囚人道路)の概略ルート: 網走→緋牛内→北見→留辺蘂→生田原→遠軽→丸瀬布→白滝→北見峠
  road: [[44.02, 144.27], [43.87, 144.05], [43.80, 143.89], [43.78, 143.62], [43.93, 143.53], [44.06, 143.53], [43.98, 143.33], [43.88, 143.15], [43.89, 143.03]].map(([a, b]) => pt(a, b)),
};
fs.writeFileSync(__dirname + '/map.js', 'window.MAP = ' + JSON.stringify(out) + ';\n');
console.log('map', W, H, d.length);
