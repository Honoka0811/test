"""背景とサムネイルを生成する(PIL)。"""
import sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
random.seed(3)
def sky(w, h):
    img = Image.new("RGB", (w, h)); px = img.load()
    top, mid, bot = (12, 10, 46), (88, 40, 120), (255, 140, 120)
    for y in range(h):
        t = y / h
        a, b, u = (top, mid, t/0.6) if t < .6 else (mid, bot, (t-.6)/.4)
        c = tuple(int(a[i] + (b[i]-a[i])*u) for i in range(3))
        for x in range(w): px[x, y] = c
    d = ImageDraw.Draw(img)
    for _ in range(int(w*h/4000)):
        x, y = random.random()*w, random.random()*h*.65; r = random.choice([1,1,1,2,3])
        d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 230))
    # 街のシルエット
    x = 0
    while x < w:
        bw = random.randint(w//40, w//14); bh = random.randint(h//12, h//4)
        d.rectangle([x, h-bh, x+bw, h], fill=(20, 14, 40))
        for wx in range(x+6, x+bw-6, 14):
            for wy in range(h-bh+8, h-10, 18):
                if random.random() < .3: d.rectangle([wx, wy, wx+5, wy+8], fill=(255, 210, 120))
        x += bw + random.randint(0, 6)
    return img
def glow_text(img, xy, text, size, fill, glow, anchor="mm", stroke=6):
    f = ImageFont.truetype(FONT, size)
    g = Image.new("RGBA", img.size, (0,0,0,0)); ImageDraw.Draw(g).text(xy, text, font=f, fill=glow, anchor=anchor, stroke_width=stroke*3, stroke_fill=glow)
    img.paste(g.filter(ImageFilter.GaussianBlur(size/6)), (0,0), g.filter(ImageFilter.GaussianBlur(size/6)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(60, 20, 90))

bg = sky(1920, 1080).convert("RGBA")
ImageDraw.Draw(bg).text((60, 50), "ミライシグナル / 歌ってみた", font=ImageFont.truetype(FONT, 40), fill=(255,255,255,200))
bg.convert("RGB").save(f"{OUT}/background.png")

th = sky(1280, 720).convert("RGBA")
ov = Image.new("RGBA", th.size, (0,0,0,0)); ImageDraw.Draw(ov).rectangle([0, 0, 1280, 720], fill=(0,0,0,40)); th = Image.alpha_composite(th, ov)
glow_text(th, (640, 300), "ミライシグナル", 170, (255,255,255), (255,90,200,255), stroke=8)
glow_text(th, (640, 470), "眠れない夜に、歌ってみた。", 64, (255,240,150), (255,120,60,255), stroke=5)
d = ImageDraw.Draw(th); f = ImageFont.truetype(FONT, 44)
d.rounded_rectangle([40, 40, 330, 110], 18, fill=(255, 60, 110)); d.text((185, 75), "オリジナル曲", font=f, fill="white", anchor="mm")
th.convert("RGB").save(f"{OUT}/thumbnail.png")
print("ok")
