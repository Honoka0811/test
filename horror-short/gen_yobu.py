"""Builds yobu.json: the script in order, with every subtitle timed from its length and every cue derived from it."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = "red"
SCRIPT = [  # (scene, key, lines[(text, class)])
 ("hook",   None,     [("電話で『もしもし』と", ""), ("二度言うのは、なんでか知っとるか。", "")]),
 ("hook",   None,     [("一度しか言えんもんが、", ""), ("おるからじゃ。", R)]),
 ("hook",   None,     [("先月死んだばあちゃんが、", ""), ("よう話してくれた。", "")]),
 ("house",  None,     [("ばあちゃんが七つの冬。", ""), ("父ちゃんが、山から戻らん晩。", "")]),
 ("shoji1", None,     [("戸の外で、声がした。", "")]),
 ("shoji1", "call1",  [("『もし』", "red big")]),
 ("shoji1", None,     [("障子に、", ""), ("父ちゃんの影が映っとった。", "")]),
 ("shoji1", None,     [("一度しか、呼ばん。", ""), ("母ちゃんは、わたしの口をふさいだ。", "")]),
 ("snow",   "reveal", [("三日後、父ちゃんは山で見つかった。", ""), ("最初の晩には、もう死んどった。", "")]),
 ("snow",   "taken",  [("山で、あれに", ""), ("返事をしてしもうたんじゃろう。", R)]),
 ("black",  "rule",   [("あれは、死んだもんの声で呼ぶ。", ""), ("一度だけ。", R)]),
 ("black",  None,     [("ええか。一度しか呼ばれんかったら、", ""), ("返事したらいかんよ。", "")]),
 ("phone",  "ring",   []),
 ("phone",  "call2",  [("『もし』", "red big")]),
 ("phone",  "none",   []),
 ("phone",  "dead",   [("二度目は、", ""), ("なかった。", R)]),
]
pages, scenes, cue = [], [], {}
t = 0.0
for i, (sc, key, lines) in enumerate(SCRIPT):
    if not scenes or scenes[-1]["k"] != sc: scenes.append({"t": round(t, 2), "k": sc})
    dts = [0.2 if i == 0 else (0.1 if key in ("call1", "call2") else 0.0)]
    for j in range(1, len(lines)): dts.append(round(dts[-1] + max(0.7, len(lines[j - 1][0]) / 6.5), 2))   # next line arrives as you finish the last
    dur = max(2.6, dts[-1] + 1.3 + len(lines[-1][0]) / 5.0) if lines else (4.2 if key == "ring" else 3.6)
    if key == "dead": dur += 1.4             # let it sit before the cut
    pages.append({"t": round(t, 2), "lines": [[d, tx, cl] for d, (tx, cl) in zip(dts, lines)]})
    if key: cue[key] = (round(t, 2), round(t + dur, 2))
    t += dur
tl = {"fps": 30, "end": round(t + 0.6, 2), "cut": round(t, 2), "scene": "scene_yobu.html", "audio": "audio_yobu.py",
      "vf": "noise=c0s=10:c0f=t,format=yuv420p", "scenes": scenes, "pages": pages,
      "call1": cue["call1"], "shadowIn": round(cue["call1"][0] + 0.5, 2),
      "reveal": cue["reveal"][0], "taken": cue["taken"][0], "rule": cue["rule"][0],
      "ring": cue["ring"][0], "answer": round(cue["ring"][1] - 0.7, 2), "call2": cue["call2"], "dead": cue["dead"][0]}
json.dump(tl, open(os.path.join(HERE, "yobu.json"), "w"), ensure_ascii=False, indent=1)
print("end", tl["end"], [(s["k"], s["t"]) for s in scenes])
