"""第2話：借金を踏み倒した男、その後（薩摩藩・調所広郷）
say の "|" は区切り。cue(k) で k 番目の区切りが始まる行内秒を取れる。
"""
from core import *

BADGE = "第2話"
QUIET_SCENES = ["end"]  # BGMを静かにするシーン

LINES = [
    dict(scene="hook",
         sub="借金500万両を踏み倒した男\nその後どうなったと思う？",
         say="借金、ごひゃくまんりょうを、踏み倒した男。|その後、どうなったと思う？"),

    dict(scene="zusho",
         sub="薩摩藩の家老\n調所広郷（ずしょ ひろさと）。",
         say="その男は、薩摩藩の家老、|ずしょひろさと。"),
    dict(scene="zusho",
         sub="もとは“茶坊主”\nお茶くみ係から大出世したの。",
         say="もとは、茶坊主。|お茶くみ係から、|大出世した人なの。"),

    dict(scene="shikumi",
         sub="借金を片付けた彼は\n“稼ぐ仕組み”を作ったの。",
         say="借金を片付けた彼は、|稼ぐ仕組みを作ったの。"),
    dict(scene="shikumi",
         sub="ひとつは奄美の黒砂糖。\n藩が独り占めして売ったの。",
         say="ひとつは、奄美の黒砂糖。|藩が独り占めして、高く売ったの。"),
    dict(scene="shikumi",
         sub="そのぶん島の人々には\nとても苦しい時代だったわ。",
         say="そのぶん、島の人々には、とても苦しい時代だったわ。"),
    dict(scene="shikumi",
         sub="もうひとつは琉球を通じた\n清（中国）との密貿易。",
         say="もうひとつは、琉球を通じた、|しんとの、密貿易。"),
    dict(scene="shikumi",
         sub="空っぽだった金庫に\n50万両の蓄えができたの！",
         say="その結果、空っぽだった金庫に、|ごじゅうまんりょうの、蓄えができたの。"),

    dict(scene="end",
         sub="でも密貿易が\n幕府にバレそうになって…",
         say="でも、密貿易が、|幕府にバレそうになって。"),
    dict(scene="end",
         sub="調所はすべての責任を\nひとりでかぶって亡くなったの。",
         say="ずしょは、すべての責任を、ひとりでかぶって、|亡くなったの。"),
    dict(scene="end",
         sub="毒を飲んだとも\n言われているわ。",
         say="毒を飲んだとも、言われているわ。"),

    dict(scene="legacy",
         sub="でも彼が残したお金が\n薩摩の近代化と倒幕を支えたの。",
         say="でも、彼が残したお金が、|薩摩の近代化と、|倒幕を支えたのよ。"),

    dict(scene="outro",
         sub="次回、長州藩の“隠し財布”の中身\nフォローしてね！",
         say="次回は、ちょうしゅうはんの、かくしざいふの中身。フォローしてね。"),
]

# ---- 小物 ----
def teacup(d, cx, cy, s):
    d.polygon([(cx - s, cy - s * 0.6), (cx + s, cy - s * 0.6), (cx + s * 0.7, cy + s * 0.6),
               (cx - s * 0.7, cy + s * 0.6)], fill=(110, 160, 110), outline=(60, 100, 60))
    d.ellipse((cx - s, cy - s * 0.75, cx + s, cy - s * 0.45), fill=(170, 210, 140))
    for k in (-0.35, 0.1, 0.5):  # 湯気
        d.arc((cx + s * k - 18, cy - s * 1.5, cx + s * k + 18, cy - s * 0.9), 90, 270, fill=CREAM, width=5)

def sugar(d, cx, cy, s):
    for i, (dx, dy) in enumerate([(-1, 0), (0, 0), (1, 0), (-0.5, -0.9), (0.5, -0.9), (0, -1.8)]):
        x, y = cx + dx * s * 1.05, cy + dy * s * 0.95
        d.rounded_rectangle((x - s / 2, y - s / 2, x + s / 2, y + s / 2), radius=s * 0.15,
                            fill=(95, 55, 30), outline=(60, 30, 15), width=3)
        d.line((x - s * 0.3, y - s * 0.25, x - s * 0.05, y - s * 0.25), fill=(140, 90, 55), width=4)

def ship(d, cx, cy, s):
    d.polygon([(cx - s, cy), (cx + s, cy), (cx + s * 0.7, cy + s * 0.4), (cx - s * 0.75, cy + s * 0.4)],
              fill=BROWN, outline=(70, 40, 20))
    d.line((cx, cy, cx, cy - s * 1.2), fill=(70, 40, 20), width=8)
    d.rectangle((cx - s * 0.55, cy - s * 1.1, cx + s * 0.55, cy - s * 0.25), fill=CREAM, outline=(150, 130, 100), width=3)
    for k in range(1, 4):
        y = cy - s * 1.1 + k * s * 0.21
        d.line((cx - s * 0.55, y, cx + s * 0.55, y), fill=(190, 170, 140), width=3)

_spot = {}
def spotlight(fr, cx, cy, r):
    key = int(r)
    if key not in _spot:
        g = Image.new("L", (key * 2, key * 2), 0)
        gd = ImageDraw.Draw(g)
        for i in range(40, 0, -1):
            rr = key * i / 40
            gd.ellipse((key - rr, key - rr, key + rr, key + rr), fill=int(70 * (1 - i / 40) ** 0.7))
        _spot[key] = Image.merge("RGBA", (Image.new("L", g.size, 255),) * 3 + (g,))
    fr.alpha_composite(_spot[key], (int(cx - key), int(cy - key)))

_dark = Image.new("RGBA", (W, H - 262), (0, 0, 10, 120))

# ---- シーン ----
def scene_hook(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.4))
    text(d, (W / 2, 420), "借金", 80 * max(p, 0.01), fill=CREAM)
    n = int(round(500 * ease_out(prog(st, 0.3, 1.2))))
    num_unit(d, W / 2, 660, f"{n}", "万両", 220, 90, fill=RED)
    text(d, (W / 2, 780), "を踏み倒した男", 76, fill=WHITE, stroke=5)
    q = ease_back(prog(lt, cue(1), 0.45))
    if q > 0:
        pulse = 1 + 0.04 * math.sin(st * 6)
        text(d, (W / 2, 1020), "その後…？", 170 * q * pulse, fill=GOLD, stroke=8)

def scene_zusho(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.4))
        person(d, W / 2, 560, 260 * max(p, 0.01), (90, 90, 130))
        text(d, (W / 2, 560), "?", 120 * p, fill=CREAM)
        a = prog(lt, 0.3, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 800), "薩摩藩 家老", 60, fill=CREAM, bold=True))
        q = ease_back(prog(lt, cue(1), 0.45))
        if q > 0:
            text(d, (W / 2, 950), "調所広郷", 150 * q, fill=GOLD, stroke=7)
            text(d, (W / 2, 1090), "ずしょ ひろさと", 52 * q, fill=WHITE, bold=True)
    else:
        q0 = ease_back(prog(lt, 0, 0.4))
        if q0 > 0:
            teacup(d, W / 2 - 250, 1100, 70 * q0)
            chip(d, W / 2 + 60, 1100, "茶坊主（お茶くみ係）", 52 * q0, fill=(110, 160, 110), fg=WHITE)
        g = ease_out(prog(lt, cue(1), 1.0))
        if g > 0:
            y1, y0 = 1010, 1010 - 420 * g
            d.line((W / 2, y1, W / 2, y0), fill=GOLD, width=22)
            d.polygon([(W / 2 - 50, y0 + 10), (W / 2 + 50, y0 + 10), (W / 2, y0 - 60)], fill=GOLD)
        q = ease_back(prog(lt, cue(2), 0.45))
        if q > 0:
            chip(d, W / 2, 480, "家老（藩の重役）", 80 * q, fill=GOLD)
            text(d, (W / 2 + 330, 760), "大出世！", 64 * q, fill=WHITE, stroke=5)

def scene_shikumi(fr, d, st, li, lt):
    if li == 4:  # 金庫に50万両
        text(d, (W / 2, 400), "空っぽだった金庫に", 62, fill=CREAM)
        k = ease_out(prog(lt, cue(1), 1.6))
        pile = [(x, y) for y in range(4) for x in range(6 - y)]
        for i, (x, y) in enumerate(pile):
            if i < k * len(pile):
                koban(d, W / 2 + (x - (5 - y) / 2) * 120, 1080 - y * 66, 54)
        n = int(round(50 * k))
        if k > 0: num_unit(d, W / 2, 700, f"{n}", "万両", 220, 90, fill=GOLD)
        if k >= 1:
            text(d, (W / 2, 1230), "財政 V字回復！", 66, fill=WHITE, stroke=5)
        return
    p = ease_back(prog(st, cue(1) if li == 0 else 0, 0.45))
    text(d, (W / 2, 400), "稼ぐ仕組み", 110 * max(p, 0.01), fill=GOLD, stroke=6)
    if li == 0:
        return
    # ① 黒砂糖
    d.rounded_rectangle((60, 500, W - 60, 820), radius=30, outline=(120, 120, 170), width=4)
    q = ease_back(prog(lt if li == 1 else 9, 0, 0.4))
    text(d, (130, 560), "①", 60, fill=GOLD)
    if q > 0:
        sugar(d, 300, 720, 64 * q)
        text(d, (680, 610), "奄美の黒砂糖", 64 * q, fill=WHITE, stroke=4)
    q = ease_back(prog(lt if li == 1 else 9, cue(1) if li == 1 else 0, 0.4))
    chip(d, 680, 730, "藩が独占して販売", 50 * q, fill=RED, fg=WHITE)
    if li >= 2:
        a = prog(lt if li == 2 else 9, 0.2, 0.4)
        faded(fr, a, lambda dd: text(dd, (W / 2, 870), "※島の人々は重い負担に苦しんだ", 44, fill=DIM, bold=True))
    if li >= 3:
        d.rounded_rectangle((60, 930, W - 60, 1250), radius=30, outline=(120, 120, 170), width=4)
        text(d, (130, 990), "②", 60, fill=GOLD)
        x = 200 + 680 * ease_out(prog(lt, 0.2, 2.6))
        ship(d, x, 1150, 70)
        q = ease_back(prog(lt, cue(1), 0.4))
        chip(d, 330, 1010, "琉球", 50 * q, fill=GREEN, fg=WHITE)
        text(d, (540, 1010), "→", 56 * q, fill=WHITE)
        chip(d, 760, 1010, "清（中国）", 50 * q, fill=RED, fg=WHITE)
        a = prog(lt, cue(1, 0.6), 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2 + 180, 1170), "密貿易", 70, fill=GOLD, stroke=5))

def scene_end(fr, d, st, li, lt):
    fr.alpha_composite(_dark, (0, 262))
    if li == 0:
        q = ease_back(prog(lt, 0, 0.4))
        text(d, (W / 2, 520), "密貿易", 100 * max(q, 0.01), fill=WHITE, stroke=5)
        r = ease_back(prog(lt, cue(1), 0.35))
        if r > 0:
            blink = RED if int(st * 6) % 2 == 0 else (255, 140, 120)
            d.ellipse((W / 2 - 170 * r, 850 - 170 * r, W / 2 + 170 * r, 850 + 170 * r), fill=blink)
            text(d, (W / 2, 850), "！", 220 * r, fill=WHITE)
            text(d, (W / 2, 1120), "幕府にバレそう…", 70 * r, fill=WHITE, stroke=5)
    else:
        spotlight(fr, W / 2, 760, 420)
        person(d, W / 2, 760, 300, (40, 40, 60))
        text(d, (W / 2, 440), "すべての責任を、ひとりで", 60, fill=CREAM, bold=True)
        if li == 1:
            a = prog(lt, cue(1), 0.8)
            faded(fr, a, lambda dd: text(dd, (W / 2, 1130), "1848年 死去", 70, fill=WHITE, stroke=4))
        else:
            text(d, (W / 2, 1130), "1848年 死去", 70, fill=WHITE, stroke=4)
            a = prog(lt, 0.3, 0.8)
            faded(fr, a, lambda dd: text(dd, (W / 2, 1240), "毒を飲んだとも…", 56, fill=DIM, bold=True))

def scene_legacy(fr, d, st, li, lt):
    steps = [("調所が残したお金", GOLD, INK), ("薩摩の近代化", (80, 90, 140), WHITE), ("倒幕へ！", RED, WHITE)]
    for k, (lab, col, fg) in enumerate(steps):
        q = ease_back(prog(lt, cue(k), 0.4))
        y = 520 + k * 260
        chip(d, W / 2, y, lab, 84 * q, fill=col, fg=fg)
        if k > 0 and q > 0:
            text(d, (W / 2, y - 132), "↓", 76, fill=WHITE)
    if prog(lt, cue(0), 0.4) > 0:
        koban(d, W / 2 - 400, 520, 46); koban(d, W / 2 + 400, 520, 46)

def scene_outro(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.45))
    chip(d, W / 2, 420, "次回予告", 56 * p, fill=RED, fg=WHITE)
    q = ease_back(prog(st, 0.5, 0.5))
    if q > 0:
        wallet(d, W / 2, 760, 200 * q, open_k=0.5 + 0.5 * math.sin(st * 4))
        text(d, (W / 2, 1010), "長州藩の", 64 * q, fill=CREAM)
        text(d, (W / 2, 1130), "“隠し財布”の中身", 92 * q, fill=GOLD, stroke=6)

SCENES = dict(hook=scene_hook, zusho=scene_zusho, shikumi=scene_shikumi,
              end=scene_end, legacy=scene_legacy, outro=scene_outro)

C = lambda k, add=0.0: ("c", k, add)  # 区切りに合わせた効果音タイミング
LINE_SE = [(0, 0.3, "coin"), (0, C(1), "kira"),
           (1, C(1), "pop"), (2, 0.0, "pop"), (2, C(2), "kira"),
           (3, C(1), "pop"), (4, 0.0, "pop"), (4, C(1), "pop"), (6, C(1), "pop"),
           (7, C(1), "coin"), (7, C(1, 0.8), "coin"), (8, C(1), "stamp"),
           (11, C(0), "pop"), (11, C(1), "pop"), (11, C(2), "don"), (12, 0.0, "kira")]
