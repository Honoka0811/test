"""第3話：長州藩の“隠し財布”の中身（撫育方）
say の "|" は区切り。cue(k) で k 番目の区切りが始まる行内秒を取れる。
"""
from core import *

BADGE = "第3話"

LINES = [
    dict(scene="hook",
         sub="幕府を倒したお金…\n実は100年前の“へそくり”！？",
         say="幕府を倒したお金。|実は、百年前の、へそくりだったの。"),

    dict(scene="hesokuri",
         sub="1762年、長州藩主\n毛利重就（もうり しげたか）。",
         say="せんななひゃくろくじゅうにねん。|ちょうしゅう藩主、もうりしげたか。"),
    dict(scene="hesokuri",
         sub="検地で増えた約4万石分を\n“別の財布”に入れたの。",
         say="検地で増えた、約よんまんごく分を、|別の財布に入れたの。"),
    dict(scene="hesokuri",
         sub="その名も「撫育方（ぶいくかた）」。\nふだんの予算とは完全に別！",
         say="その名も、ぶいくかた。|ふだんの予算とは、完全に別。"),
    dict(scene="hesokuri",
         sub="ふだんの赤字には使わない\n“とっておき”のお金なの。",
         say="ふだんの赤字には使わない、|とっておきのお金なの。"),
    dict(scene="hesokuri",
         sub="新田開発や港の商売でも増やして\nコツコツ100年！",
         say="しんでん開発や、港の商売でも増やして、|コツコツ百年。"),

    dict(scene="bakumatsu",
         sub="そして幕末。幕府は長州に\n武器が渡らないようにしたの。",
         say="そして幕末。|幕府は、長州に、武器が渡らないようにしたの。"),
    dict(scene="bakumatsu",
         sub="そこで間に入ったのが\n坂本龍馬！",
         say="そこで、間に入ったのが、|坂本龍馬。"),
    dict(scene="bakumatsu",
         sub="薩摩の名義で\n最新の銃を数千丁も買ったの。",
         say="薩摩の名義で、|最新の銃を、数千丁も買ったの。"),
    dict(scene="bakumatsu",
         sub="その銃で長州は\n幕府軍に勝っちゃった！",
         say="その銃で、ちょうしゅうは、|幕府軍に、勝っちゃった。"),

    dict(scene="outro",
         sub="100年前のへそくりが\n日本を変えたのね。",
         say="百年前のへそくりが、|日本を変えたのね。"),
    dict(scene="outro",
         sub="シリーズ完結！次に知りたい藩を\nコメントで教えてね！",
         say="シリーズ完結。|次に知りたい藩を、コメントで教えてね。"),
]

# ---- 小物 ----
def lock(d, cx, cy, s):
    d.arc((cx - s * 0.55, cy - s * 1.25, cx + s * 0.55, cy - s * 0.15), 180, 360, fill=(200, 200, 215), width=int(s * 0.2))
    d.line((cx - s * 0.55 + s * 0.1, cy - s * 0.7, cx - s * 0.55 + s * 0.1, cy - s * 0.3), fill=(200, 200, 215), width=int(s * 0.2))
    d.line((cx + s * 0.55 - s * 0.1, cy - s * 0.7, cx + s * 0.55 - s * 0.1, cy - s * 0.3), fill=(200, 200, 215), width=int(s * 0.2))
    d.rounded_rectangle((cx - s * 0.8, cy - s * 0.4, cx + s * 0.8, cy + s * 0.7), radius=s * 0.15, fill=GOLD,
                        outline=(170, 120, 30), width=5)
    d.ellipse((cx - s * 0.13, cy - s * 0.05, cx + s * 0.13, cy + s * 0.21), fill=INK)
    d.rectangle((cx - s * 0.05, cy + s * 0.1, cx + s * 0.05, cy + s * 0.42), fill=INK)

def rifle(d, cx, cy, s, col=(170, 170, 190)):
    d.rectangle((cx - s, cy - s * 0.06, cx + s * 0.55, cy + s * 0.06), fill=col)
    d.polygon([(cx + s * 0.4, cy - s * 0.08), (cx + s * 1.0, cy - s * 0.04), (cx + s * 1.05, cy + s * 0.3),
               (cx + s * 0.85, cy + s * 0.32), (cx + s * 0.4, cy + s * 0.12)], fill=BROWN)

# ---- シーン ----
def scene_hook(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.4))
    text(d, (W / 2, 430), "幕府を倒したお金", 84 * max(p, 0.01), fill=WHITE, stroke=5)
    q = ease_back(prog(lt, cue(1), 0.45))
    if q > 0:
        wallet(d, W / 2, 790, 220 * q, open_k=0.5 + 0.5 * math.sin(st * 4))
        text(d, (W / 2, 1060), "100年前の", 70 * q, fill=CREAM)
        text(d, (W / 2, 1190), "へそくり！？", 120 * q, fill=GOLD, stroke=7)

def scene_hesokuri(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.4))
        text(d, (W / 2, 520), "1762年", 170 * max(p, 0.01), fill=WHITE, stroke=7)
        text(d, (W / 2, 680), "（江戸時代の中ごろ）", 50, fill=DIM, bold=True)
        q = ease_back(prog(lt, cue(1), 0.45))
        if q > 0:
            text(d, (W / 2, 880), "長州藩主", 64 * q, fill=CREAM)
            text(d, (W / 2, 1010), "毛利重就", 140 * q, fill=GOLD, stroke=7)
            text(d, (W / 2, 1140), "もうり しげたか", 50 * q, fill=WHITE, bold=True)
        return
    if li == 1:
        text(d, (W / 2, 420), "検地で増えた分", 66, fill=CREAM)
        n = int(round(4 * ease_out(prog(lt, 0.4, 0.8))))
        num_unit(d, W / 2, 640, f"+{n}", "万石", 200, 90, fill=GOLD)
        g = ease_out(prog(lt, cue(1), 0.8))
        if g > 0:
            y = 700 + 120 * g
            koban(d, W / 2, y, 50)
            wallet(d, W / 2, 1000, 190 * ease_back(prog(lt, cue(1), 0.4)))
            text(d, (W / 2, 1220), "別の財布へ", 64, fill=WHITE, stroke=4)
        return
    # li >= 2：撫育方
    if li == 2:
        p = ease_back(prog(lt, 0, 0.45))
        text(d, (W / 2, 430), "撫育方", 150 * max(p, 0.01), fill=GOLD, stroke=7)
        text(d, (W / 2, 560), "ぶいくかた", 50 * p, fill=WHITE, bold=True)
        q = ease_back(prog(lt, cue(1), 0.45))
        if q > 0:
            for x, lab, col in [(W / 2 - 230, "ふだんの予算", (90, 90, 130)), (W / 2 + 230, "撫育方", BROWN)]:
                d.rounded_rectangle((x - 200 * q, 720, x + 200 * q, 1080), radius=26, fill=col)
                text(d, (x, 790), lab, 50 * q, fill=WHITE)
            koban(d, W / 2 + 230, 950, 70 * q)
            text(d, (W / 2 - 230, 950), "赤字…", 54 * q, fill=(255, 150, 140))
            d.line((W / 2, 690, W / 2, 1110), fill=RED, width=14)
            text(d, (W / 2, 1200), "完全に別会計！", 66 * q, fill=WHITE, stroke=5)
    elif li == 3:
        text(d, (W / 2, 430), "撫育方", 110, fill=GOLD, stroke=6)
        wallet(d, W / 2, 800, 210)
        q = ease_back(prog(lt, 0.5, 0.45))
        if q > 0: lock(d, W / 2 + 190, 900, 110 * q)
        r = ease_back(prog(lt, cue(1), 0.45))
        chip(d, W / 2, 1150, "とっておき", 84 * r, fill=GOLD)
    else:
        text(d, (W / 2, 420), "コツコツ増やす", 70, fill=CREAM)
        chips = [("新田開発", GREEN, 0.0), ("港の商売", (60, 110, 170), 1.0)]
        for lab, col, at in chips:
            q = ease_back(prog(lt, at, 0.4))
            chip(d, W / 2 - 230 if at == 0 else W / 2 + 230, 560, lab, 56 * q, fill=col, fg=WHITE)
        # 年表バー
        g = ease_out(prog(lt, cue(1), 1.4))
        x0, x1, y = 140, W - 140, 760
        d.rounded_rectangle((x0, y - 14, x1, y + 14), radius=14, fill=(70, 70, 110))
        d.rounded_rectangle((x0, y - 14, x0 + (x1 - x0) * g, y + 14), radius=14, fill=GOLD)
        text(d, (x0, y + 60), "1762", 44, fill=CREAM, bold=True)
        text(d, (x1, y + 60), "幕末", 44, fill=CREAM, bold=True)
        pile = [(x, yy) for yy in range(4) for x in range(6 - yy)]
        for i, (x, yy) in enumerate(pile):
            if i < g * len(pile):
                koban(d, W / 2 + (x - (5 - yy) / 2) * 110, 1160 - yy * 60, 50)
        n = int(round(100 * g))
        if g > 0: text(d, (W / 2, 900), f"{n}年", 90, fill=WHITE, stroke=5)

def scene_bakumatsu(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.4))
        text(d, (W / 2, 450), "幕末", 150 * max(p, 0.01), fill=WHITE, stroke=7)
        q = ease_back(prog(lt, cue(1), 0.45))
        if q > 0:
            chip(d, W / 2 - 280, 800, "武器", 76 * q, fill=(80, 90, 140), fg=WHITE)
            chip(d, W / 2 + 280, 800, "長州", 76 * q, fill=RED, fg=WHITE)
            w = int(16 * q)
            d.line((W / 2 - 60 * q, 740, W / 2 + 60 * q, 860), fill=RED, width=w)
            d.line((W / 2 + 60 * q, 740, W / 2 - 60 * q, 860), fill=RED, width=w)
            text(d, (W / 2, 1000), "幕府が売らせない！", 66 * q, fill=WHITE, stroke=5)
    elif li == 1:
        text(d, (W / 2, 450), "そこで間に入ったのが", 60, fill=CREAM)
        q = ease_back(prog(lt, cue(1), 0.45))
        if q > 0:
            spot_r = 360 * q
            d.ellipse((W / 2 - spot_r, 800 - spot_r, W / 2 + spot_r, 800 + spot_r), outline=GOLD, width=8)
            text(d, (W / 2, 760), "坂本龍馬", 130 * q, fill=GOLD, stroke=7)
            text(d, (W / 2, 900), "（亀山社中）", 52 * q, fill=CREAM, bold=True)
    elif li == 2:
        q = ease_back(prog(lt, 0, 0.4))
        chip(d, W / 2, 440, "薩摩の名義で購入", 70 * q, fill=GOLD)
        k = ease_out(prog(lt, cue(1), 1.4))
        for i in range(12):
            if i < k * 12:
                rifle(d, W / 2 - 250 + (i % 3) * 250, 620 + (i // 3) * 130, 100)
        if k > 0.95:
            text(d, (W / 2, 1220), "最新の銃 数千丁！", 76, fill=WHITE, stroke=5)
    else:
        text(d, (W / 2, 460), "長州 vs 幕府軍", 90, fill=WHITE, stroke=5)
        stamp(fr, W / 2, 800, "長州の勝利", prog(lt, cue(1), 0.25))
        a = prog(lt, cue(1, 0.6), 0.4)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1080), "1866年 第二次長州征討", 52, fill=DIM, bold=True))

def scene_outro(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.45))
    if p > 0:
        wallet(d, W / 2 - 260, 520, 130 * p)
        text(d, (W / 2 + 140, 520), "100年前の\nへそくり", 64 * p, fill=CREAM)
    q = ease_back(prog(st, 0.2 + (cue(1) if li == 0 else 0), 0.45)) if li == 0 else 1
    if q > 0:
        text(d, (W / 2, 720), "↓", 80 * q, fill=WHITE)
        text(d, (W / 2, 880), "日本を変えた", 130 * q, fill=GOLD, stroke=7)
    if li == 1:
        r = ease_back(prog(lt, 0, 0.45))
        chip(d, W / 2, 1060, "シリーズ完結", 60 * r, fill=RED, fg=WHITE)
        s = ease_back(prog(lt, cue(1), 0.45))
        if s > 0:
            d.rounded_rectangle((W / 2 - 400 * s, 1240 - 75 * s, W / 2 + 400 * s, 1240 + 75 * s), radius=36, fill=WHITE)
            text(d, (W / 2, 1240), "次に知りたい藩は？", 64 * s, fill=INK)

SCENES = dict(hook=scene_hook, hesokuri=scene_hesokuri, bakumatsu=scene_bakumatsu, outro=scene_outro)

C = lambda k, add=0.0: ("c", k, add)
LINE_SE = [(0, C(1), "kira"), (1, 0.0, "don"), (1, C(1), "pop"),
           (2, 0.4, "pop"), (2, C(1), "coin"), (3, 0.0, "pop"), (3, C(1), "stamp"),
           (4, 0.5, "pop"), (4, C(1), "kira"), (5, 0.0, "pop"), (5, 1.0, "pop"), (5, C(1), "coin"),
           (6, C(1), "stamp"), (7, C(1), "kira"), (8, 0.0, "pop"), (8, C(1), "coin"),
           (9, C(1), "stamp"), (10, C(1), "kira"), (11, 0.0, "pop"), (11, C(1), "pop")]
