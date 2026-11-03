# -*- coding: utf-8 -*-
"""SVG illustration parts for the video. Flat, friendly style. viewBox 0 0 760 700."""

FONT = "IPAPGothic, IPAGothic, sans-serif"

def sun(x, y, r=46, color="#f6c344"):
    rays = ""
    import math
    for i in range(8):
        a = i * math.pi / 4
        x1, y1 = x + math.cos(a) * (r + 14), y + math.sin(a) * (r + 14)
        x2, y2 = x + math.cos(a) * (r + 34), y + math.sin(a) * (r + 34)
        rays += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="7" stroke-linecap="round"/>'
    return f'<g>{rays}<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/></g>'

def cloud(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s})" fill="#ffffff" opacity="0.95">'
            '<ellipse cx="0" cy="0" rx="60" ry="30"/><circle cx="-30" cy="-6" r="28"/>'
            '<circle cx="10" cy="-18" r="34"/><circle cx="42" cy="-4" r="26"/></g>')

def sky_ground(ground_y=470, ground="#9bcf7f", ground2="#7fb866"):
    return (f'<rect x="0" y="0" width="760" height="700" fill="#dff1fb"/>'
            f'<path d="M0 {ground_y} Q 200 {ground_y-60} 420 {ground_y-10} T 760 {ground_y-30} V700 H0 Z" fill="{ground}"/>'
            f'<path d="M0 {ground_y+90} Q 260 {ground_y+30} 760 {ground_y+70} V700 H0 Z" fill="{ground2}"/>')

def crop_rows(x, y, w, n=4, gap=38, color="#8a5a33", sprout="#4b9a3e"):
    out = ""
    for i in range(n):
        yy = y + i * gap
        out += f'<path d="M{x} {yy} Q {x+w/2} {yy-10} {x+w} {yy}" stroke="{color}" stroke-width="14" fill="none" stroke-linecap="round"/>'
        for j in range(6):
            sx = x + 30 + j * (w - 60) / 5
            sy = yy - 8 - (3 if j % 2 else 0)
            out += (f'<path d="M{sx} {sy} q -10 -14 -16 -6 M{sx} {sy} q 10 -14 16 -6 M{sx} {sy} v -16" '
                    f'stroke="{sprout}" stroke-width="5" fill="none" stroke-linecap="round"/>')
    return out

def person(x, y, kind="farmer", s=1.0, shirt=None, skin="#f7d4b8"):
    """Standing person about 200px tall at scale 1, feet at (x, y)."""
    shirts = {"salary": "#3f5a8a", "farmer": "#4c8a3f", "young": "#e0734a", "old": "#6f7f8c", "worker": "#2f8f8f", "staff": "#8a5fb0"}
    shirt = shirt or shirts.get(kind, "#4c8a3f")
    hair = "#4a3426" if kind != "old" else "#c9c9c9"
    g = f'<g transform="translate({x},{y}) scale({s})">'
    # legs
    pants = "#2d2d3a" if kind == "salary" else "#5b6b8a"
    g += f'<rect x="-30" y="-70" width="24" height="70" rx="8" fill="{pants}"/><rect x="6" y="-70" width="24" height="70" rx="8" fill="{pants}"/>'
    g += '<rect x="-34" y="-10" width="32" height="12" rx="6" fill="#3a2a1a"/><rect x="2" y="-10" width="32" height="12" rx="6" fill="#3a2a1a"/>'
    # body
    g += f'<rect x="-42" y="-170" width="84" height="108" rx="26" fill="{shirt}"/>'
    # arms
    g += f'<rect x="-66" y="-162" width="24" height="90" rx="12" fill="{shirt}"/><rect x="42" y="-162" width="24" height="90" rx="12" fill="{shirt}"/>'
    g += f'<circle cx="-54" cy="-70" r="13" fill="{skin}"/><circle cx="54" cy="-70" r="13" fill="{skin}"/>'
    # head
    g += f'<circle cx="0" cy="-205" r="40" fill="{skin}"/>'
    g += f'<path d="M-40 -212 Q -30 -252 0 -248 Q 32 -252 40 -212 Q 20 -228 0 -226 Q -20 -228 -40 -212 Z" fill="{hair}"/>'
    # face
    g += '<circle cx="-14" cy="-206" r="4" fill="#333"/><circle cx="14" cy="-206" r="4" fill="#333"/>'
    g += '<path d="M-12 -190 Q 0 -180 12 -190" stroke="#8a4b3a" stroke-width="4" fill="none" stroke-linecap="round"/>'
    g += '<circle cx="-24" cy="-192" r="6" fill="#f5a9a0" opacity="0.7"/><circle cx="24" cy="-192" r="6" fill="#f5a9a0" opacity="0.7"/>'
    if kind == "salary":
        g += '<path d="M0 -168 l -9 -14 h 18 Z M0 -168 l -7 40 l 7 12 l 7 -12 Z" fill="#c33d3d"/>'
        g += '<rect x="-46" y="-166" width="92" height="20" fill="#ffffff" opacity="0.9"/>'
        g += '<path d="M0 -168 l -9 -14 h 18 Z M0 -166 l -7 40 l 7 12 l 7 -12 Z" fill="#c33d3d"/>'
        g += '<rect x="60" y="-80" width="50" height="40" rx="6" fill="#5a3b21"/><rect x="76" y="-90" width="18" height="12" rx="4" fill="none" stroke="#5a3b21" stroke-width="5"/>'
    if kind in ("farmer", "old"):
        g += '<ellipse cx="0" cy="-236" rx="66" ry="14" fill="#e3b961"/><path d="M-38 -238 Q -36 -278 0 -278 Q 36 -278 38 -238 Z" fill="#edc872"/>'
        g += '<rect x="-38" y="-246" width="76" height="8" fill="#b4432f"/>'
    if kind == "worker":
        g += '<path d="M-40 -230 Q 0 -270 40 -230 Z" fill="#2f8f8f"/><rect x="-44" y="-236" width="88" height="10" rx="4" fill="#206d6d"/>'
        g += '<rect x="-32" y="-160" width="64" height="12" rx="4" fill="#ffffff" opacity="0.8"/>'
    if kind == "young":
        g += '<path d="M-40 -214 Q -36 -256 0 -250 Q 30 -256 40 -216 Q 30 -236 10 -232 Q -10 -246 -40 -214 Z" fill="#5a3b26"/>'
    g += '</g>'
    return g

def hoe(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s})"><line x1="0" y1="0" x2="60" y2="-190" stroke="#8a5a33" stroke-width="10" stroke-linecap="round"/>'
            '<path d="M-6 6 l 34 -18 l 10 20 l -34 18 Z" fill="#6b7a86"/></g>')

def arrow(x1, y1, x2, y2, color="#e0734a", w=14):
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    hx, hy = x2 - math.cos(a) * 26, y2 - math.sin(a) * 26
    px, py = -math.sin(a) * 22, math.cos(a) * 22
    return (f'<line x1="{x1}" y1="{y1}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>'
            f'<polygon points="{x2},{y2} {hx+px:.1f},{hy+py:.1f} {hx-px:.1f},{hy-py:.1f}" fill="{color}"/>')

def building(x, y, w=170, h=230, color="#8fa3b8", win="#dff1fb"):
    g = f'<g transform="translate({x},{y})"><rect x="0" y="{-h}" width="{w}" height="{h}" rx="6" fill="{color}"/>'
    cols = int(w // 46)
    rows = int(h // 52)
    for r in range(rows):
        for c in range(cols):
            g += f'<rect x="{14 + c*46}" y="{-h + 16 + r*52}" width="26" height="28" rx="3" fill="{win}"/>'
    g += f'<rect x="{w/2-22}" y="-46" width="44" height="46" rx="4" fill="#4a5a6a"/></g>'
    return g

def greenhouse(x, y, w=240, h=120):
    return (f'<g transform="translate({x},{y})"><path d="M0 0 V{-h+60} Q 0 {-h} {w/2} {-h} Q {w} {-h} {w} {-h+60} V0 Z" fill="#cfeefb" stroke="#7aaec9" stroke-width="6"/>'
            + "".join(f'<line x1="{i*w/6}" y1="{-h+60 if i in (0,6) else -h+14}" x2="{i*w/6}" y2="0" stroke="#7aaec9" stroke-width="4"/>' for i in range(1, 6))
            + f'<line x1="0" y1="{-h+60}" x2="{w}" y2="{-h+60}" stroke="#7aaec9" stroke-width="4"/>'
            + "".join(f'<path d="M{20+i*40} -10 q -8 -22 -16 -10 M{20+i*40} -10 q 8 -22 16 -10 M{20+i*40} -10 v -24" stroke="#4b9a3e" stroke-width="4" fill="none" stroke-linecap="round"/>' for i in range(w // 40))
            + '</g>')

def tractor(x, y, s=1.0, color="#d9423a"):
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<rect x="-10" y="-120" width="120" height="70" rx="10" fill="{color}"/>'
            f'<rect x="-120" y="-90" width="130" height="50" rx="10" fill="{color}"/>'
            '<rect x="20" y="-180" width="70" height="66" rx="8" fill="#3a3a48"/><rect x="28" y="-172" width="54" height="40" rx="4" fill="#cfeefb"/>'
            '<rect x="-100" y="-150" width="10" height="60" fill="#3a3a48"/>'
            '<circle cx="60" cy="-40" r="56" fill="#2b2b33"/><circle cx="60" cy="-40" r="30" fill="#c9c9c9"/>'
            '<circle cx="-80" cy="-32" r="34" fill="#2b2b33"/><circle cx="-80" cy="-32" r="16" fill="#c9c9c9"/>'
            '</g>')

def money_bag(x, y, s=1.0, label="¥"):
    return (f'<g transform="translate({x},{y}) scale({s})"><path d="M-70 0 Q -80 -90 -20 -110 L -30 -140 H 30 L 20 -110 Q 80 -90 70 0 Z" fill="#e9b949" stroke="#c9922a" stroke-width="5"/>'
            '<rect x="-34" y="-146" width="68" height="14" rx="6" fill="#c9922a"/>'
            f'<text x="0" y="-30" text-anchor="middle" font-size="60" font-weight="bold" fill="#8a5a1a" font-family="{FONT}">{label}</text></g>')

def coin(x, y, r=26):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f1cf62" stroke="#c9922a" stroke-width="4"/>'
            f'<text x="{x}" y="{y+10}" text-anchor="middle" font-size="{r}" font-weight="bold" fill="#8a5a1a" font-family="{FONT}">¥</text>')

def document(x, y, w=190, h=250, stamp=None, title="農地取得の申請"):
    g = f'<g transform="translate({x},{y})"><rect x="6" y="6" width="{w}" height="{h}" rx="8" fill="#c9c2a8"/><rect x="0" y="0" width="{w}" height="{h}" rx="8" fill="#ffffff" stroke="#b9b29a" stroke-width="3"/>'
    g += f'<text x="{w/2}" y="40" text-anchor="middle" font-size="20" fill="#3a3a3a" font-family="{FONT}">{title}</text>'
    for i in range(6):
        g += f'<rect x="22" y="{66+i*26}" width="{w-44 - (40 if i%3==2 else 0)}" height="10" rx="5" fill="#d9d4c2"/>'
    if stamp:
        g += (f'<g transform="translate({w-62},{h-62}) rotate(-12)"><circle r="42" fill="none" stroke="#d9423a" stroke-width="5"/>'
              f'<text y="12" text-anchor="middle" font-size="34" font-weight="bold" fill="#d9423a" font-family="{FONT}">{stamp}</text></g>')
    g += '</g>'
    return g

def signpost(x, y, labels, colors=("#4c8a3f", "#2f8f8f", "#e0734a")):
    g = f'<g transform="translate({x},{y})"><rect x="-10" y="-300" width="20" height="300" fill="#8a5a33"/>'
    for i, (lab, col) in enumerate(zip(labels, colors)):
        yy = -290 + i * 78
        g += (f'<path d="M-130 {yy} H 110 l 24 24 l -24 24 H -130 Z" fill="{col}"/>'
              f'<text x="-8" y="{yy+32}" text-anchor="middle" font-size="26" font-weight="bold" fill="#fff" font-family="{FONT}">{lab}</text>')
    g += '</g>'
    return g

def fence(x, y, n=6, gap=44):
    g = f'<g transform="translate({x},{y})">'
    for i in range(n):
        g += f'<rect x="{i*gap}" y="-70" width="12" height="70" rx="3" fill="#c9a06c"/>'
    g += f'<rect x="-6" y="-56" width="{(n-1)*gap+24}" height="10" fill="#c9a06c"/><rect x="-6" y="-26" width="{(n-1)*gap+24}" height="10" fill="#c9a06c"/></g>'
    return g

def board_sign(x, y, text, w=200, color="#f6f3e7"):
    return (f'<g transform="translate({x},{y})"><rect x="{w/2-8}" y="-40" width="16" height="60" fill="#8a5a33"/>'
            f'<rect x="0" y="-110" width="{w}" height="76" rx="10" fill="{color}" stroke="#8a5a33" stroke-width="6"/>'
            f'<text x="{w/2}" y="-60" text-anchor="middle" font-size="30" font-weight="bold" fill="#3d7a4a" font-family="{FONT}">{text}</text></g>')

def label(x, y, text, size=28, color="#2b3a2f", weight="bold", anchor="middle"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}" font-family="{FONT}">{text}</text>'

def bubble(x, y, w, h, text, size=26, fill="#ffffff", color="#2b3a2f", tail="left"):
    tx = x + 40 if tail == "left" else x + w - 40
    g = (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="#cfd8c8" stroke-width="3"/>'
         f'<polygon points="{tx-14},{y+h-1} {tx+14},{y+h-1} {tx},{y+h+22}" fill="{fill}" stroke="#cfd8c8" stroke-width="3"/>'
         f'<rect x="{tx-16}" y="{y+h-6}" width="32" height="8" fill="{fill}"/>')
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        g += label(x + w / 2, y + h / 2 + (i - (len(lines) - 1) / 2) * (size + 8) + size / 3, ln, size=size, color=color)
    g += '</g>'
    return g

def wrap(inner):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 700" width="760" height="700">{inner}</svg>'

# ---------------- composed scenes ----------------

def scene_title():
    s = sky_ground(480)
    s += sun(640, 110, 50) + cloud(150, 120, 1.1) + cloud(420, 80, 0.8)
    s += crop_rows(400, 540, 340, n=4)
    s += building(40, 470, 150, 210)
    s += person(190, 500, "salary", 0.95)
    s += arrow(300, 380, 430, 380, "#e0734a", 16)
    s += person(560, 500, "farmer", 0.95) + hoe(620, 500, 0.95)
    s += label(190, 560, "会社員", 30, "#2b3a2f") + label(560, 560, "農家", 30, "#2b3a2f")
    return wrap(s)

def scene_paths():
    s = sky_ground(430)
    s += sun(120, 110, 44) + cloud(520, 110, 1.0)
    s += signpost(430, 620, ["① 新規就農", "② 雇用就農", "③ 継承"])
    s += person(150, 640, "salary", 0.9)
    s += bubble(60, 330, 230, 90, "どのルートが\n自分に合う？", 24)
    return wrap(s)

def scene_permit():
    s = sky_ground(440)
    s += cloud(600, 100, 1.0) + sun(130, 110, 40)
    s += fence(400, 560, 7, 46)
    s += crop_rows(400, 620, 320, n=2)
    s += document(60, 300, 200, 250, stamp="許可", title="農地の取得申請")
    s += label(160, 590, "農業委員会の許可", 24, "#2b3a2f")
    s += person(320, 690, "salary", 0.75)
    s += label(560, 530, "農地", 30, "#2b3a2f")
    return wrap(s)

def scene_consult():
    s = f'<rect x="0" y="0" width="760" height="700" fill="#f3efe0"/>'
    s += '<rect x="0" y="520" width="760" height="180" fill="#d8cfb3"/>'
    s += '<rect x="330" y="400" width="400" height="130" rx="10" fill="#8a5a33"/><rect x="330" y="400" width="400" height="18" fill="#6e4426"/>'
    s += '<rect x="80" y="60" width="600" height="110" rx="14" fill="#3d7a4a"/>'
    s += label(380, 130, "新規就農相談窓口", 46, "#ffffff")
    s += person(560, 400, "staff", 0.8)
    s += person(190, 530, "salary", 0.9)
    s += bubble(250, 220, 300, 110, "研修先・農地・\n支援制度をまとめて案内", 24)
    s += document(620, 220, 110, 140, title="制度一覧")
    return wrap(s)

def scene_own_farm():
    s = sky_ground(420)
    s += sun(640, 100, 48) + cloud(180, 100, 1.0)
    s += crop_rows(60, 520, 420, n=5, gap=36)
    s += board_sign(350, 560, "じぶん農園", 220)
    s += person(640, 690, "farmer", 0.95) + hoe(700, 690, 0.95)
    s += greenhouse(60, 420, 200, 110)
    return wrap(s)

def scene_steps():
    s = f'<rect x="0" y="0" width="760" height="700" fill="#f3efe0"/>'
    steps = [("①", "相談・情報収集", "#2f8f8f"), ("②", "研修 1〜2年", "#4c8a3f"), ("③", "農地・資金・住まい", "#e0734a"), ("④", "就農！", "#d9423a")]
    for i, (num, t, col) in enumerate(steps):
        y = 110 + i * 140
        s += f'<circle cx="110" cy="{y}" r="46" fill="{col}"/>' + label(110, y + 16, num, 44, "#fff")
        s += f'<rect x="190" y="{y-44}" width="500" height="88" rx="16" fill="#ffffff" stroke="{col}" stroke-width="5"/>'
        s += label(440, y + 14, t, 36, "#2b3a2f")
        if i < 3:
            s += f'<line x1="110" y1="{y+50}" x2="110" y2="{y+90}" stroke="#9aa39a" stroke-width="8" stroke-dasharray="12 10"/>'
    return wrap(s)

def scene_money():
    s = f'<rect x="0" y="0" width="760" height="700" fill="#f3efe0"/>'
    s += '<rect x="60" y="80" width="280" height="200" rx="10" fill="#c7d1dc"/><polygon points="40,90 200,20 360,90" fill="#8fa3b8"/>'
    for i in range(4):
        s += f'<rect x="{85+i*64}" y="130" width="34" height="150" fill="#ffffff"/>'
    s += label(200, 310, "国・自治体", 28)
    s += arrow(360, 190, 470, 190, "#e0734a", 14)
    s += money_bag(560, 320, 1.1)
    s += label(560, 370, "就農準備資金・経営開始資金", 22) + label(560, 404, "年間最大150万円", 30, "#d9423a")
    s += coin(120, 520) + coin(170, 540) + coin(220, 520)
    s += label(170, 600, "青年等就農資金（無利子融資）", 24)
    s += tractor(560, 620, 0.8)
    s += label(560, 660, "機械・施設の導入に", 22)
    return wrap(s)

def scene_company():
    s = sky_ground(440)
    s += sun(90, 100, 40) + cloud(420, 100, 1.0)
    s += building(60, 470, 180, 230, "#8fa3b8")
    s += '<rect x="70" y="250" width="160" height="40" rx="6" fill="#3d7a4a"/>' + label(150, 280, "○○農業法人", 22, "#fff")
    s += greenhouse(300, 470, 240, 120)
    s += greenhouse(560, 470, 180, 100)
    s += person(300, 680, "worker", 0.85) + person(420, 680, "worker", 0.85, shirt="#2f8f8f") + person(540, 680, "worker", 0.85)
    s += person(660, 680, "salary", 0.85)
    s += bubble(560, 230, 190, 80, "よろしく\nお願いします！", 20, tail="right")
    return wrap(s)

def scene_jobsearch():
    s = f'<rect x="0" y="0" width="760" height="700" fill="#f3efe0"/>'
    s += '<rect x="80" y="70" width="600" height="380" rx="18" fill="#2b3a2f"/><rect x="100" y="90" width="560" height="340" rx="10" fill="#ffffff"/>'
    s += '<rect x="100" y="90" width="560" height="54" rx="10" fill="#3d7a4a"/>' + label(380, 128, "農業求人サイト", 28, "#fff")
    for i in range(3):
        y = 165 + i * 85
        s += f'<rect x="120" y="{y}" width="520" height="70" rx="8" fill="#f3efe0"/>'
        s += f'<rect x="135" y="{y+14}" width="42" height="42" rx="6" fill="{["#4c8a3f","#e0734a","#2f8f8f"][i]}"/>'
        s += label(200, y + 34, ["野菜生産スタッフ　月給◯◯万円", "果樹園 正社員　未経験歓迎", "酪農ヘルパー　研修制度あり"][i], 22, "#2b3a2f", anchor="start")
        s += label(200, y + 58, ["住宅手当あり・社会保険完備", "就農準備資金の対象", "寮あり"][i], 16, "#6a7a6a", anchor="start")
    s += '<rect x="330" y="450" width="100" height="40" fill="#2b3a2f"/><rect x="230" y="490" width="300" height="16" rx="8" fill="#2b3a2f"/>'
    s += person(160, 700, "salary", 0.65)
    s += label(470, 600, "農業をはじめる.JP / 農業会議 / ハローワーク", 22) + label(470, 640, "就農フェアで直接相談も", 22)
    return wrap(s)

def scene_handover():
    s = sky_ground(460)
    s += sun(380, 100, 48) + cloud(120, 110, 0.9) + cloud(620, 130, 0.9)
    s += crop_rows(60, 560, 640, n=3, gap=40)
    s += tractor(170, 490, 0.7)
    s += greenhouse(470, 490, 200, 100)
    s += person(250, 690, "old", 0.95)
    s += person(510, 690, "young", 0.95)
    s += '<g transform="translate(380,520)"><rect x="-70" y="-14" width="140" height="28" rx="14" fill="#e9b949"/><circle cx="-70" cy="0" r="22" fill="#e9b949" stroke="#c9922a" stroke-width="4"/></g>'
    s += label(380, 470, "経営を引き継ぐ", 28)
    s += label(250, 560 - 300, "引退する農家", 24) + label(510, 560 - 300, "就農希望者", 24)
    return wrap(s)

def scene_matching():
    s = f'<rect x="0" y="0" width="760" height="700" fill="#f3efe0"/>'
    s += '<rect x="230" y="60" width="300" height="120" rx="16" fill="#3d7a4a"/>'
    s += label(380, 110, "農業経営・就農支援センター", 24, "#fff") + label(380, 150, "民間マッチングサービス", 24, "#fff")
    s += arrow(300, 190, 180, 320, "#e0734a", 12) + arrow(460, 190, 580, 320, "#e0734a", 12)
    s += person(170, 560, "old", 0.9) + person(590, 560, "young", 0.9)
    s += label(170, 600, "後継者を探す農家", 24) + label(590, 600, "就農したい人", 24)
    s += '<rect x="250" y="400" width="260" height="150" rx="14" fill="#ffffff" stroke="#cfd8c8" stroke-width="3"/>'
    s += label(380, 440, "まとめて引き継ぐもの", 22, "#6a7a6a")
    s += label(380, 480, "農地　機械・ハウス", 26) + label(380, 520, "販路（売り先）　ノウハウ", 26)
    s += arrow(230, 460, 255, 460, "#2f8f8f", 8) + arrow(530, 460, 505, 460, "#2f8f8f", 8)
    return wrap(s)

def scene_compare():
    s = f'<rect x="0" y="0" width="760" height="700" fill="#f3efe0"/>'
    cols = [("① 新規就農", "#4c8a3f"), ("② 雇用就農", "#2f8f8f"), ("③ 継承", "#e0734a")]
    rows = [("初期費用", ["大", "ほぼ不要", "中"]), ("リスク", ["高", "低", "中"]), ("自由度", ["高", "低", "中"]), ("収入の安定", ["低（当初）", "高", "中"])]
    x0, y0, cw, rh = 170, 80, 190, 110
    for i, (t, col) in enumerate(cols):
        s += f'<rect x="{x0+i*cw}" y="{y0}" width="{cw-8}" height="70" rx="10" fill="{col}"/>' + label(x0 + i * cw + (cw - 8) / 2, y0 + 46, t, 26, "#fff")
    for r, (rn, vals) in enumerate(rows):
        y = y0 + 80 + r * rh
        s += f'<rect x="20" y="{y}" width="140" height="{rh-10}" rx="10" fill="#2b3a2f"/>' + label(90, y + rh / 2 + 4, rn, 24, "#fff")
        for i, v in enumerate(vals):
            colr = {"大": "#d9423a", "高": "#d9423a", "ほぼ不要": "#4c8a3f", "低": "#4c8a3f", "中": "#e0a030", "低（当初）": "#d9423a"}.get(v, "#2b3a2f")
            s += f'<rect x="{x0+i*cw}" y="{y}" width="{cw-8}" height="{rh-10}" rx="10" fill="#ffffff"/>' + label(x0 + i * cw + (cw - 8) / 2, y + rh / 2 + 6, v, 34 if len(v) <= 2 else 24, colr)
    s += label(380, 640, "※ 一般的な傾向。地域・作物・個人の状況で変わります", 20, "#6a7a6a")
    return wrap(s)

def scene_checklist():
    s = sky_ground(470)
    s += sun(640, 100, 44) + cloud(160, 110, 1.0)
    s += '<rect x="90" y="60" width="360" height="470" rx="18" fill="#c9a06c"/><rect x="110" y="100" width="320" height="410" rx="10" fill="#ffffff"/>'
    s += '<rect x="210" y="40" width="120" height="50" rx="12" fill="#6e4426"/>'
    items = ["いきなり辞めない", "何を作るか決める", "早めに窓口へ相談", "家族の理解・生活費"]
    for i, t in enumerate(items):
        y = 150 + i * 90
        s += f'<rect x="135" y="{y-22}" width="44" height="44" rx="8" fill="none" stroke="#3d7a4a" stroke-width="5"/>'
        s += f'<path d="M143 {y} l 12 12 l 24 -28" stroke="#3d7a4a" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        s += label(200, y + 10, t, 26, "#2b3a2f", anchor="start")
    s += person(600, 690, "farmer", 0.95) + hoe(660, 690, 0.95)
    s += crop_rows(470, 560, 260, n=2)
    return wrap(s)

def scene_ending():
    s = sky_ground(440)
    s += '<rect x="0" y="0" width="760" height="440" fill="url(#g1)"/>'
    s = s.replace('<rect x="0" y="0" width="760" height="700" fill="#dff1fb"/>', '<defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f9d5a0"/><stop offset="1" stop-color="#dff1fb"/></linearGradient></defs><rect x="0" y="0" width="760" height="700" fill="#dff1fb"/>')
    s += sun(380, 400, 70, "#f6a63a")
    s += '<path d="M0 440 Q 200 380 420 430 T 760 410 V700 H0 Z" fill="#9bcf7f"/><path d="M0 560 Q 260 500 760 540 V700 H0 Z" fill="#7fb866"/>'
    s += crop_rows(60, 600, 640, n=2, gap=44)
    s += person(300, 690, "farmer", 1.0) + hoe(360, 690, 1.0)
    s += person(460, 690, "young", 1.0)
    s += cloud(130, 120, 1.0) + cloud(620, 90, 0.9)
    return wrap(s)

SCENES = {
    "title": scene_title, "paths": scene_paths, "permit": scene_permit, "consult": scene_consult,
    "own_farm": scene_own_farm, "steps": scene_steps, "money": scene_money, "company": scene_company,
    "jobsearch": scene_jobsearch, "handover": scene_handover, "matching": scene_matching,
    "compare": scene_compare, "checklist": scene_checklist, "ending": scene_ending,
}
