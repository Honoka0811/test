"""Build 1940-style map layers (Natural Earth via world-atlas) clipped to East Asia / Pacific."""
import json, math, os, pickle
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from timeline import HERE

SRC = os.path.join(HERE, "..", "geo", "package", "countries-10m.json")
BBOX = box(108, -2, 172, 58)

def merc_y(lat): return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))

def decode(topo):
    tr = topo["transform"]; sx, sy = tr["scale"]; tx, ty = tr["translate"]
    arcs = []
    for a in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out
    geoms = {}
    for g in topo["objects"]["countries"]["geometries"]:
        polys = []
        if g["type"] == "Polygon": parts = [g["arcs"]]
        elif g["type"] == "MultiPolygon": parts = g["arcs"]
        else: continue
        for p in parts:
            rings = [ring(r) for r in p]
            if len(rings[0]) < 4: continue
            try:
                polys.append(Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0))
            except Exception: pass
        geoms[(g.get("id"), g["properties"]["name"])] = unary_union(polys) if polys else None
    return geoms

def to_list(geom):
    if geom is None or geom.is_empty: return []
    if isinstance(geom, Polygon): geom = [geom]
    elif hasattr(geom, "geoms"): geom = [g for g in geom.geoms if isinstance(g, Polygon)]
    out = []
    for p in geom:
        c = np.array(p.exterior.coords)
        c[:, 1] = [merc_y(v) for v in c[:, 1]]
        out.append(c.astype(np.float32))
    return out

def main():
    geoms = decode(json.load(open(SRC)))
    by_id = {}
    for (i, n), g in geoms.items():
        if g is None: continue
        g = g.intersection(BBOX)
        if g.is_empty: continue
        by_id.setdefault(i, []).append((n, g))
    def get(i): return unary_union([g for _, g in by_id.get(i, [])]) if i in by_id else Polygon()
    rus, chn, jpn = get("643"), get("156"), get("392")
    kuril_box = box(145.2, 43.0, 157.0, 50.8)
    hoppo_box = box(145.2, 43.0, 149.2, 45.7)
    kara_box = box(140.5, 45.8, 145.2, 50.0)
    kanto_box = Polygon([(120.8, 38.6), (122.4, 38.6), (122.4, 39.25), (121.9, 39.45), (121.3, 39.45), (120.8, 39.2)])
    layers = {
        "naichi": unary_union([jpn, rus.intersection(kuril_box)]),
        "hoppo": rus.intersection(hoppo_box),
        "chosen": unary_union([get("410"), get("408")]),
        "taiwan": get("158"),
        "kanto": chn.intersection(kanto_box),
        "karafuto": rus.intersection(kara_box),
        "nanyo": unary_union([get("585"), get("580"), get("583"), get("584")]),
    }
    special = unary_union([v for k, v in layers.items() if k != "hoppo"])
    others = []
    for i, lst in by_id.items():
        for n, g in lst:
            others.append(g)
    other = unary_union(others).difference(special)
    out = {"other": to_list(other.simplify(0.01))}
    for k, v in layers.items():
        out[k] = to_list(v.simplify(0.004))
    for k, v in out.items(): print(k, len(v), sum(len(p) for p in v))
    pickle.dump(out, open(os.path.join(HERE, "map.pkl"), "wb"))

if __name__ == "__main__":
    main()
