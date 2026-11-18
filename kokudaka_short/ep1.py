"""第1話：石高ゼロの大名と、隠れた稼ぎ"""
from core import *

BADGE = "第1話"

# 台本：sub = 字幕、say = 読み上げ用（読み間違い対策でひらがな化）
# テーマ：「石高（表の数字）より“隠れた稼ぎ”が時代を動かした」
LINES = [
    dict(scene="hook",
         sub="石高ゼロなのに\n大名だった藩、知ってる？",
         say="こくだかゼロなのに、大名だった藩、知ってる？"),

    dict(scene="matsumae",
         sub="北海道の松前藩。\n寒くてお米が取れないの。",
         say="北海道の、マツマエハン。寒くて、おこめが取れないの。"),
    dict(scene="matsumae",
         sub="そこでアイヌとの交易で\n昆布や鮭を売って稼いだの！",
         say="そこで、アイヌの人々との交易で、昆布や、さけを売って、稼いでいたの。"),

    dict(scene="scale",
         sub="そもそも石高は\nとれるお米の量のこと。",
         say="そもそも、こくだかは、とれる、おこめの量のこと。"),
    dict(scene="scale",
         sub="1石は1人が1年で食べる量。\n今なら数万〜10万円ほど。",
         say="いっこくは、ひとりが一年で食べる量。今のお金で、数万円から十万円ほど。"),
    dict(scene="scale",
         sub="つまり加賀百万石は\n100万人を食べさせられる国！",
         say="つまり、かがひゃくまんごくは、百万人を食べさせられる国なの。"),

    dict(scene="satsuma",
         sub="でも、大きい藩ほど\nお金に苦しんでいたの。",
         say="でも、大きい藩ほど、お金に苦しんでいたの。"),
    dict(scene="satsuma",
         sub="77万石の薩摩藩、借金500万両。\n今なら数千億円とも！",
         say="ななじゅうななまんごくの、さつまはん。借金は、ごひゃくまんりょう。今なら、数千億円とも言われるわ。"),
    dict(scene="satsuma",
         sub="そこで出した答えが…\n「無利子で250年払い」",
         say="そこで出した答えが、無利子で、にひゃくごじゅうねん払い。"),
    dict(scene="satsuma",
         sub="ほぼ踏み倒しよ！",
         say="ほぼ、踏み倒しよ。"),

    dict(scene="choshu",
         sub="長州藩は表向き37万石。\nでも裏に“隠し財布”があったの。",
         say="ちょうしゅうはんは、表向き、さんじゅうななまんごく。でも裏に、かくしざいふがあったの。"),
    dict(scene="choshu",
         sub="貯めたお金で最新の武器を買い\n幕府を倒しちゃった。",
         say="ためたお金で、最新の武器を買って、幕府を倒しちゃった。"),

    dict(scene="outro",
         sub="時代を動かしたのは\n石高じゃなく“隠れた稼ぎ”。",
         say="時代を動かしたのは、こくだかじゃなく、隠れた稼ぎだったのね。"),
    dict(scene="outro",
         sub="次回、借金を踏み倒した男の\nその後…フォローしてね！",
         say="次回は、借金を踏み倒した男の、その後。フォローしてね。"),
]

# ---------------- シーン ----------------
# 各関数: (frame, draw, シーン内時刻, シーン内の行番号, 行内時刻)

def scene_hook(fr, d, st, li, lt):
    n = int(round(102 * (1 - ease_out(prog(st, 0.1, 1.0)))))
    shake = 12 * math.sin(st * 60) * clamp(1.5 - st) if n == 0 else 0
    text(d, (W / 2, 440), "石高", 90, fill=CREAM)
    num_unit(d, W / 2 + shake, 860, f"{n}", "石", 380, 120, fill=RED if n == 0 else WHITE, stroke=10)
    p = ease_back(prog(st, 1.3, 0.45))
    chip(d, W / 2, 1060, "なのに大名！？", 84 * p, fill=GOLD)

def snow(d, st, n=40):
    for i in range(n):
        x = (i * 137.5) % W + 30 * math.sin(st * 1.5 + i)
        y = 280 + ((i * 263 + st * (90 + (i % 5) * 25)) % 1000)
        r = 5 + (i % 4) * 3
        d.ellipse((x - r, y - r, x + r, y + r), fill=(235, 240, 255))

def scene_matsumae(fr, d, st, li, lt):
    snow(d, st)
    p = ease_back(prog(st, 0, 0.45))
    text(d, (W / 2, 420), "松前藩", 150 * max(p, 0.01), fill=GOLD, stroke=6)
    text(d, (W / 2, 560), "（いまの北海道）", 56, fill=CREAM, bold=True)
    if li == 0:
        q = ease_back(prog(lt, 1.0, 0.45))
        if q > 0: bowl_crossed(d, W / 2, 860, 170 * q)
    else:
        items = [("交易", W / 2 - 300, GOLD, INK, 1.2), ("昆布", W / 2, GREEN, WHITE, 2.2), ("鮭", W / 2 + 300, RED, WHITE, 2.8)]
        for lab, x, col, fg, at in items:
            q = ease_back(prog(lt, at, 0.4))
            chip(d, x, 800, lab, 84 * q, fill=col, fg=fg)
        q = ease_back(prog(lt, 3.8, 0.45))
        if q > 0:
            text(d, (W / 2, 950), "↓", 90 * q, fill=WHITE)
            text(d, (W / 2, 1110), "お米ゼロでも稼げた！", 80 * q, fill=GOLD, stroke=6)

def scene_scale(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.45))
        text(d, (W / 2, 450), "石高とは？", 110 * max(p, 0.01), fill=WHITE, stroke=5)
        q = ease_back(prog(lt, 0.6, 0.45))
        if q > 0: rice_sack(d, W / 2, 800, 220 * q)
        a = prog(lt, 1.2, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1110), "＝ とれるお米の量", 76, fill=GOLD, stroke=5))
    elif li == 1:
        rice_sack(d, W / 2 - 250, 520, 150)
        text(d, (W / 2 + 170, 470), "1石", 120, fill=GOLD, stroke=5)
        text(d, (W / 2 + 170, 590), "約150kg", 56, fill=CREAM, bold=True)
        q = ease_back(prog(lt, 1.0, 0.4))
        if q > 0:
            person(d, W / 2 - 120, 800, 120 * q, CREAM)
            text(d, (W / 2 + 120, 810), "1人の1年分", 64 * q, fill=WHITE, stroke=4)
        q = ease_back(prog(lt, 3.2, 0.45))
        if q > 0:
            d.rounded_rectangle((W / 2 - 420 * q, 1040 - 95 * q, W / 2 + 420 * q, 1040 + 95 * q),
                                radius=30, fill=RED)
            text(d, (W / 2, 1040), "今なら 数万〜10万円", 70 * q, fill=WHITE)
    else:
        text(d, (W / 2, 400), "加賀藩", 100, fill=GOLD, stroke=5)
        n = int(round(102 * ease_out(prog(lt, 0.1, 1.2))))
        num_unit(d, W / 2, 660, f"{n}", "万石", 220, 90)
        cols, rows, s = 10, 4, 70
        x0, y0 = W / 2 - (cols - 1) * 92 / 2, 800
        k = ease_out(prog(lt, 1.6, 1.4)) * cols * rows
        for i in range(cols * rows):
            if i < k:
                person(d, x0 + (i % cols) * 92, y0 + (i // cols) * 78, s, GOLD if i % 7 else CREAM)
        a = prog(lt, 2.8, 0.3)
        faded(fr, a, lambda dd: text(dd, (W / 2, 1180), "100万人を食べさせられる国！", 66, fill=WHITE, stroke=5))

def scene_satsuma(fr, d, st, li, lt):
    if li == 0:
        p = ease_back(prog(lt, 0, 0.45))
        text(d, (W / 2, 520), "大きい藩ほど", 90 * max(p, 0.01), fill=CREAM)
        q = ease_back(prog(lt, 0.7, 0.45))
        if q > 0:
            text(d, (W / 2, 730), "財政は", 90 * q, fill=WHITE)
            text(d, (W / 2, 920), "火の車", 190 * q, fill=(255, 120, 50), stroke=8)
        return
    text(d, (W / 2, 380), "薩摩藩（77万石）", 72, fill=GOLD, stroke=4)
    if li == 1:
        # 小判が積み上がる
        k = ease_out(prog(lt, 1.8, 2.0))
        pile = [(x, y) for y in range(5) for x in range(7 - y)]
        for i, (x, y) in enumerate(pile):
            if i < k * len(pile):
                cx = W / 2 + (x - (6 - y) / 2) * 120
                koban(d, cx, 1090 - y * 66, 54)
        n = int(round(500 * ease_out(prog(lt, 2.4, 1.4))))
        text(d, (W / 2, 470), "借金", 64, fill=CREAM, bold=True)
        num_unit(d, W / 2, 700, f"{n}", "万両", 200, 90, fill=RED)
        a = ease_back(prog(lt, 4.4, 0.45))
        chip(d, W / 2, 1250, "今なら数千億円！？", 70 * a, fill=RED, fg=WHITE)
    else:
        q = ease_back(prog(lt if li == 2 else 9, 1.4, 0.4))
        chip(d, W / 2, 560, "無利子", 90 * q, fill=GREEN, fg=WHITE)
        n = int(round(250 * ease_out(prog(lt if li == 2 else 9, 2.0, 0.9))))
        if li == 3 or lt > 2.0:
            num_unit(d, W / 2, 900, f"{n}", "年払い", 260, 100, fill=GOLD)
        if li == 3:
            stamp(fr, W / 2, 1110, "ほぼ踏み倒し", prog(lt, 0, 0.25))

def scene_choshu(fr, d, st, li, lt):
    text(d, (W / 2, 390), "長州藩", 110, fill=GOLD, stroke=5)
    if li == 0:
        text(d, (W / 2, 540), "表向きは 37万石", 64, fill=CREAM, stroke=4)
        q = ease_back(prog(lt, 3.6, 0.5))
        if q > 0:
            wallet(d, W / 2, 860, 230 * q, open_k=0.5 + 0.5 * math.sin(st * 4))
            text(d, (W / 2, 1120), "裏の“隠し財布”", 80 * q, fill=GOLD, stroke=6)
    else:
        steps = [("隠し財布", BROWN, WHITE), ("最新の武器", (80, 90, 140), WHITE), ("幕府を倒す！", RED, WHITE)]
        for k, (lab, col, fg) in enumerate(steps):
            q = ease_back(prog(lt, (0.1, 1.1, 2.4)[k], 0.4))
            y = 580 + k * 230
            chip(d, W / 2, y, lab, 84 * q, fill=col, fg=fg)
            if k > 0 and q > 0:
                text(d, (W / 2, y - 118), "↓", 70, fill=WHITE)

def scene_outro(fr, d, st, li, lt):
    p = ease_back(prog(st, 0, 0.5))
    text(d, (W / 2, 450), "時代を動かしたのは", 70 * max(p, 0.01), fill=CREAM)
    q = ease_back(prog(st, 1.8, 0.45))
    if q > 0:
        text(d, (W / 2, 610), "石高", 80 * q, fill=DIM)
        d.line((W / 2 - 100 * q, 610, W / 2 + 100 * q, 610), fill=RED, width=10)
    r = ease_back(prog(st, 2.6, 0.5))
    if r > 0:
        text(d, (W / 2, 790), "隠れた稼ぎ", 150 * r, fill=GOLD, stroke=8)
    if li == 1:
        q = ease_back(prog(lt, 0, 0.45))
        if q > 0:
            d.rounded_rectangle((W / 2 - 380 * q, 1060 - 100 * q, W / 2 + 380 * q, 1060 + 100 * q),
                                radius=40, fill=WHITE)
            d.polygon([(W / 2 - 60 * q, 1060 + 95 * q), (W / 2 + 10 * q, 1060 + 95 * q),
                       (W / 2 - 90 * q, 1060 + 160 * q)], fill=WHITE)
            text(d, (W / 2, 1020), "次回予告", 44 * q, fill=DIM)
            text(d, (W / 2, 1090), "踏み倒した男のその後…", 62 * q, fill=RED)

SCENES = dict(hook=scene_hook, matsumae=scene_matsumae, scale=scene_scale,
              satsuma=scene_satsuma, choshu=scene_choshu, outro=scene_outro)

# 効果音（行番号, 行内の秒, 種類）
LINE_SE = [(0, 1.3, "kira"), (1, 1.0, "pop"), (2, 1.2, "pop"), (2, 2.2, "pop"), (2, 2.8, "pop"),
           (2, 3.8, "kira"), (3, 0.6, "pop"), (4, 1.0, "pop"), (4, 3.2, "pop"), (5, 1.4, "kira"),
           (7, 1.8, "coin"), (7, 2.8, "coin"), (7, 4.4, "pop"), (8, 1.4, "pop"), (8, 2.9, "kira"),
           (9, 0.0, "stamp"), (10, 3.6, "coin"), (11, 0.1, "pop"), (11, 1.1, "pop"), (11, 2.4, "don"),
           (12, 2.4, "kira"), (13, 0.0, "pop")]

