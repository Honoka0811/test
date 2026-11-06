"""27秒付近(ほぼ満杯)のフレームに大きな文字を重ねたサムネイル。"""
import subprocess
from PIL import Image, ImageDraw, ImageFont
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "27.5", "-i", "output/every_bounce_bigger.mp4",
                "-frames:v", "1", "output/_thumb_src.png"], check=True)
im = Image.open("output/_thumb_src.png").convert("RGB")
d = ImageDraw.Draw(im)
d.rectangle([0, 0, 1080, 520], fill=(8, 8, 16))
d.rectangle([0, 1480, 1080, 1920], fill=(8, 8, 16))
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 130)
for y, s, c in ((170, "CAN IT", (255, 255, 255)), (320, "FILL IT?", (255, 220, 60))):
    w = d.textlength(s, font=f)
    d.text(((1080 - w) / 2, y), s, font=f, fill=c, stroke_width=10, stroke_fill=(0, 0, 0))
f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
s = "SATISFYING ENDING"
d.text(((1080 - d.textlength(s, font=f2)) / 2, 1600), s, font=f2, fill=(120, 255, 160), stroke_width=8, stroke_fill=(0, 0, 0))
im.save("output/thumbnail.png")
