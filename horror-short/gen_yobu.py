"""Builds yobu.json: the script in order, with every subtitle timed from its length and every cue derived from it."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = "red"
SCRIPT = [  # (scene, key, lines[(text, class)])
 ("hook",   None,     [("夜、名前を呼ばれても、", ""), ("一度目で返事をしたらいかん。", "")]),
 ("house",  None,     [("人は、二度呼ぶ。", ""), ("山のもんは、一度しか呼ばん。", R)]),
 ("house",  None,     [("七つの冬。", ""), ("父ちゃんが山から戻らん晩。", "")]),
 ("shoji1", None,     [("戸の外で、声がした。", "")]),
 ("shoji1", "call1",  [("『キヨ』", "red big")]),
 ("shoji1", None,     [("障子に、", ""), ("父ちゃんの影が映っとった。", "")]),
 ("shoji1", None,     [("けど、一度しか呼ばん。", ""), ("母ちゃんは、わたしの口をふさいだ。", "")]),
 ("shoji1", None,     [("影は、朝まで動かんかった。", "")]),
 ("snow",   None,     [("朝。雪の上に、", ""), ("足あとは、ひとつも無かった。", R)]),
 ("shoji2", None,     [("次の晩。", "")]),
 ("shoji2", "call2",  [("『キヨ。キヨ』", "red big")]),
 ("shoji2", None,     [("二度、呼ばれた。", ""), ("二度呼ぶのは、人のはずじゃ。", "")]),
 ("shoji2", "reach",  [("『父ちゃんが帰った』", ""), ("母ちゃんが、戸に手をかけた。", "")]),
 ("shoji2", None,     [("『月も出とらんのに、", ""), ("なんで影が映っとるん』", "")]),
 ("shoji2", "stretch", [("母ちゃんは、手を引っこめた。", ""), ("戸は、朝まで開けんかった。", "")]),
 ("snow",   None,     [("三日後、", ""), ("父ちゃんは山で見つかった。", "")]),
 ("snow",   "reveal", [("最初の晩には、もう", ""), ("死んどったそうじゃ。", R)]),
 ("snow",   None,     [("あれは、人のまねを覚える。", ""), ("帰りを待っとる人の姿で来る。", R)]),
 ("black",  None,     [("あれから七十年。", ""), ("あれは、いまも来る。", "")]),
 ("black",  None,     [("あんたの父ちゃんは、", ""), ("今夜、まだ帰っとらんね。", "")]),
 ("shoji3", "call3",  [("今夜は、三度呼んだ。", ""), ("あんたの父ちゃんの声じゃ。", R)]),
 ("shoji3", None,     [("月は、出とらん。", ""), ("なのに、影が映っとる。", R)]),
 ("shoji3", "poke",   []),
 ("shoji3", "last",   [("ええか。", ""), ("返事を、したらいかんよ。", R)]),
]
pages, scenes, cue = [], [], {}
t = 0.0
for i, (sc, key, lines) in enumerate(SCRIPT):
    if not scenes or scenes[-1]["k"] != sc: scenes.append({"t": round(t, 2), "k": sc})
    dts = [0.2 if i == 0 else (0.1 if key in ("call1", "call2") else 0.0)]
    for j in range(1, len(lines)): dts.append(round(dts[-1] + max(0.7, len(lines[j - 1][0]) / 6.5), 2))   # next line arrives as you finish the last
    dur = max(2.6, dts[-1] + 1.3 + len(lines[-1][0]) / 5.0) if lines else 3.4
    if key == "call3": dur += 1.6            # three knocks first
    if key == "call3": dts = [round(d + 1.9, 2) for d in dts]
    pages.append({"t": round(t, 2), "lines": [[d, tx, cl] for d, (tx, cl) in zip(dts, lines)]})
    if key: cue[key] = (round(t, 2), round(t + dur, 2))
    t += dur
tl = {"fps": 30, "end": round(t + 0.6, 2), "cut": round(t, 2), "scene": "scene_yobu.html", "audio": "audio_yobu.py",
      "vf": "noise=c0s=10:c0f=t,format=yuv420p", "scenes": scenes, "pages": pages,
      "knock1": cue["call1"][0] + 0.1, "shadowIn": round(cue["call1"][0] + 0.4, 2),
      "knock2": [round(cue["call2"][0] + 0.1, 2), round(cue["call2"][0] + 0.85, 2)],
      "arm": [round(cue["reach"][0] + 1.6, 2), round(cue["stretch"][0] + 0.2, 2)],
      "stretch": [round(cue["stretch"][0] + 0.3, 2), cue["stretch"][1]],
      "reveal": cue["reveal"][0],
      "knock3": [round(cue["call3"][0] + 0.2 + k * 0.75, 2) for k in range(3)],
      "poke": round(cue["poke"][0] + 0.3, 2), "hole": round(cue["poke"][0] + 0.7, 2), "eye": round(cue["poke"][0] + 1.7, 2),
      "lastText": cue["last"][0]}
json.dump(tl, open(os.path.join(HERE, "yobu.json"), "w"), ensure_ascii=False, indent=1)
print("end", tl["end"], [(s["k"], s["t"]) for s in scenes])
