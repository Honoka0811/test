"""Builds yobu.json: the script in order, with every subtitle timed from its length and every cue derived from it."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = "red"
SCRIPT = [  # (scene, key, lines[(text, class)])
 ("hook",      None,     [("電話で『もしもし』と", ""), ("二度言うのは、なんでか知っとるか。", "")]),
 ("hook",      None,     [("一度しか言えんもんが、", ""), ("おるからじゃ。", R)]),
 ("house",     None,     [("ばあちゃんが七つの冬。", ""), ("父ちゃんが、山から戻らん晩。", "")]),
 ("shoji1",    None,     [("戸の外で、声がした。", "")]),
 ("shoji1",    "call1",  [("『もし』", "red big")]),
 ("shoji1",    None,     [("月も出とらんのに、", ""), ("障子に、父ちゃんの影が映っとった。", R)]),
 ("shoji1",    None,     [("一度しか、呼ばん。", ""), ("母ちゃんは、わたしの口をふさいだ。", "")]),
 ("snow",      None,     [("朝。雪の上に、", ""), ("足あとは、無かった。", "")]),
 ("snow",      "reveal", [("三日後、父ちゃんは山で見つかった。", ""), ("最初の晩には、もう死んどった。", "")]),
 ("snow",      "taken",  [("山で、あれに", ""), ("返事をしてしもうたんじゃろう。", R)]),
 ("black",     None,     [("あれは、人のまねを覚える。", ""), ("声も、しゃべり方も。", "")]),
 ("black",     None,     [("何十年、かけてでも。", R)]),
 ("shojiRoom", "room",   [("じゃから、ええか。", ""), ("『もしもし』と二度呼ばれたら、", ""), ("それは人じゃ。返事してええ。", "")]),
 ("shojiRoom", "lamp",   [("ほら、もう寝んさい。", "")]),
 ("shojiRoom", "quiet",  []),
 ("shojiRoom", "call2",  [("『もしもし』", "mid")]),
 ("shojiRoom", "tell",   [("灯りは消えとるのに、", ""), ("影が映っとる。", R)]),
 ("shojiRoom", "dead",   [("ばあちゃんは、", ""), ("先月、死んだ。", R)]),
]
pages, scenes, cue = [], [], {}
t = 0.0
for i, (sc, key, lines) in enumerate(SCRIPT):
    if not scenes or scenes[-1]["k"] != sc: scenes.append({"t": round(t, 2), "k": sc})
    dts = [0.2 if i == 0 else (0.1 if key in ("call1", "call2") else 0.0)]
    for j in range(1, len(lines)): dts.append(round(dts[-1] + max(0.7, len(lines[j - 1][0]) / 6.5), 2))   # next line arrives as you finish the last
    dur = max(2.6, dts[-1] + 1.3 + len(lines[-1][0]) / 5.0) if lines else 3.2
    if key == "dead": dur += 1.4             # let it sit before the cut
    pages.append({"t": round(t, 2), "lines": [[d, tx, cl] for d, (tx, cl) in zip(dts, lines)]})
    if key: cue[key] = (round(t, 2), round(t + dur, 2))
    t += dur
tl = {"fps": 30, "end": round(t + 0.6, 2), "cut": round(t, 2), "scene": "scene_yobu.html", "audio": "audio_yobu.py",
      "vf": "noise=c0s=10:c0f=t,format=yuv420p", "scenes": scenes, "pages": pages,
      "call1": cue["call1"], "shadowIn": round(cue["call1"][0] + 0.5, 2),
      "reveal": cue["reveal"][0], "taken": cue["taken"][0], "room": cue["room"][0],
      "lampOff": round(cue["lamp"][0] + 2.5, 2), "call2": cue["call2"], "tell": cue["tell"][0], "dead": cue["dead"][0]}
json.dump(tl, open(os.path.join(HERE, "yobu.json"), "w"), ensure_ascii=False, indent=1)
print("end", tl["end"], [(s["k"], s["t"]) for s in scenes])
