"""timeline.json（ナレーションの時刻）から、映像と音の両方が使う演出タイミング cues.json を作る。"""
import json, sys, pathlib

B = pathlib.Path(sys.argv[1])
tl = json.loads((B / "voice" / "timeline.json").read_text())
S = {s["id"]: s for s in tl["scenes"]}


def ph(sid, kana):
    s = S[sid]
    for p in s["phrases"]:
        if kana in p["kana"]:
            return round(s["start"] + p["t"], 3)
    raise KeyError(f"{sid}: {kana}")


def reveal(sid):
    s = S[sid]
    if sid == "rice":
        return ph("rice", "ヨンセン")
    i = next(i for i, p in enumerate(s["phrases"]) if p["kana"].endswith("カラ"))
    return round(s["start"] + s["phrases"][i + 1]["t"], 3)


items = [s["id"] for s in tl["scenes"] if s["type"] in ("item", "rice")]
cues = {
    "total": tl["total"],
    "hook": [ph("hook", "コノ"), ph("hook", "ブッカ"), ph("hook", "ココマデ")],
    "intro": [ph("intro", "ニセンジュウ"), ph("intro", "イマノ"), ph("intro", "クラベテ")],
    "reveal": {i: reveal(i) for i in items},
    "stamp": {i: (ph("rice", "ニバイ") if i == "rice" else round(reveal(i) + 0.42, 3)) for i in items},
    # お米：ピーク（4000円超）から現在価格へ下がる瞬間と、「4割高い」スタンプ
    "drop": round(ph("rice", "ハッピャク") - 0.3, 3),
    "stamp2": ph("rice", "ヨンワリ"),
    "chartStart": S["chart"]["start"],
    "cpi": ph("chart", "ブッカシスウ"),
    "glow": ph("chart", "ミノマワリ"),
    "why": [ph("why", "エンヤス"), ph("why", "エネルギイ"), ph("why", "ジンケン")],
    "cta": S["cta"]["start"],
    "comment": ph("cta", "コメント"),
}

sfx = [{"t": 0.6, "k": "impact"}]
sfx += [{"t": t, "k": "hit"} for t in cues["hook"][1:]]
sfx += [{"t": t, "k": "whoosh"} for t in cues["intro"][:2]]
for i in items:
    if i != "rice":
        sfx += [{"t": S[i]["start"] - 0.05, "k": "whoosh"},
                {"t": cues["reveal"][i], "k": "coin"},
                {"t": cues["stamp"][i], "k": "stamp"}]
sfx += [{"t": S["rice"]["start"] - 0.05, "k": "whoosh"},
        {"t": S["rice"]["start"] + 0.4, "k": "riser", "until": cues["reveal"]["rice"]},
        {"t": cues["reveal"]["rice"], "k": "impact"},
        {"t": cues["stamp"]["rice"], "k": "stamp"},
        {"t": cues["drop"], "k": "down"},
        {"t": cues["stamp2"], "k": "stamp"}]
sfx += [{"t": S["chart"]["start"] - 0.05, "k": "whoosh"}]
sfx += [{"t": cues["chartStart"] + 0.25 + 0.13 * k, "k": "tick"} for k in range(8)]
sfx += [{"t": cues["cpi"], "k": "pop"}, {"t": cues["glow"], "k": "hit"}]
sfx += [{"t": S["why"]["start"] - 0.05, "k": "whoosh"}]
sfx += [{"t": t, "k": "pop"} for t in cues["why"]]
sfx += [{"t": cues["cta"] - 0.05, "k": "whoosh"}, {"t": cues["comment"], "k": "pop"}]
cues["sfx"] = sorted(sfx, key=lambda e: e["t"])

(B / "cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1))
print(json.dumps({k: v for k, v in cues.items() if k != "sfx"}, ensure_ascii=False))
