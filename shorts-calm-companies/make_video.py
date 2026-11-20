"""穏やかな人が多いと言われる企業10選 — 縦型ショート動画を生成する。

必要なもの:
  - VOICEVOX ENGINE が localhost:50021 で起動していること
      docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-latest
  - ffmpeg, Pillow
  - フォント M PLUS Rounded 1c (FONT_DIR に配置)

使い方: python3 make_video.py [FONT_DIR]
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
FONT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "fonts"
ENGINE = "http://localhost:50021"
SPEAKER = 2  # 四国めたん（ノーマル）
SPEED = 1.12
W, H = 1080, 1920
FPS = 30

BOLD = str(FONT_DIR / "mplus800.ttf")
MED = str(FONT_DIR / "mplus500.ttf")

# 配色（落ち着いたグリーン×クリーム）
BG_TOP = (232, 244, 236)
BG_BOTTOM = (250, 246, 236)
INK = (38, 54, 48)
ACCENT = (62, 140, 110)
ACCENT_SOFT = (200, 228, 214)
METAN = (196, 72, 132)  # 四国めたんのイメージカラー（ピンク）

TITLE = ("穏やかな人が多い", "と言われる企業10選")

# (表示名, 業界タグ, 画面の理由テキスト, ナレーション)
COMPANIES = [
    ("三井不動産", "不動産", "「人の三井」\n協調性を大切にする社風",
     "まずは、三井不動産。「人の三井」と呼ばれ、協調性を大切にする社風ですわ。"),
    ("三井住友信託銀行", "信託銀行", "メガバンクより落ち着いた\n真面目で温厚な雰囲気",
     "三井住友信託銀行。メガバンクより落ち着いた、真面目で温厚な雰囲気ですの。"),
    ("味の素", "食品", "人を大切にする社風\n働き方改革も進む",
     "味の素。人を大切にする社風で、働き方改革も進んでいますわ。"),
    ("花王", "日用品", "誠実で堅実\nチームワーク重視",
     "花王。誠実で堅実、チームワークを重んじる会社ですわ。"),
    ("中外製薬", "製薬", "落ち着いた製薬業界の中でも\n働きやすさの評価が高い",
     "中外製薬。落ち着いた人が多い製薬業界でも、働きやすさの評価が高いんですの。"),
    ("NTTデータ", "IT・SIer", "面倒見が良く\n温厚な人が多い",
     "エヌティーティーデータ。面倒見が良く、温厚な人が多いと言われますわ。"),
    ("東京ガス", "インフラ", "競争より協調\n安定志向の社風",
     "東京ガス。インフラ企業らしく、競争より協調を重んじる雰囲気ですわ。"),
    ("日本郵船", "海運", "品が良く\n穏やかな人が多い",
     "にっぽんゆうせん。品が良く、穏やかな人が多いと評判ですの。"),
    ("キリンHD", "飲料", "社員同士の仲が良く\n和やかな雰囲気",
     "キリンホールディングス。社員同士の仲が良く、和やかな雰囲気ですわ。"),
    ("日本政策投資銀行", "政府系金融", "ノルマの圧力が少なく\n知的で落ち着いた人が多い",
     "にっぽん政策投資銀行。ノルマの圧力が少なく、知的で落ち着いた人が多いですわ。"),
]

INTRO_NARR = "穏やかな人が多いと言われる企業、10選をご紹介しますわ！"
OUTRO_NARR = ("ただし、雰囲気は部署や上司によって変わりますわ。"
              "口コミやオービー訪問で、ご自分の目で確かめてくださいましね。")
OUTRO_LINES = ["※雰囲気は部署・上司で変わります",
               "口コミサイトやOB・OG訪問で",
               "自分の目で確かめよう"]


# ---------- 音声 ----------
def tts(text: str, out: Path) -> float:
    q = urllib.parse.urlencode({"text": text, "speaker": SPEAKER})
    req = urllib.request.Request(f"{ENGINE}/audio_query?{q}", method="POST")
    query = json.load(urllib.request.urlopen(req))
    query["speedScale"] = SPEED
    query["prePhonemeLength"] = 0.15
    query["postPhonemeLength"] = 0.35
    req = urllib.request.Request(
        f"{ENGINE}/synthesis?speaker={SPEAKER}",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    out.write_bytes(urllib.request.urlopen(req).read())
    with wave.open(str(out)) as w:
        return w.getnframes() / w.getframerate()


# ---------- 描画ヘルパー ----------
def font(path, size):
    return ImageFont.truetype(path, size)


def background():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    # やわらかい円の装飾
    deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    for (cx, cy, r, a) in [(120, 260, 260, 60), (980, 900, 320, 45), (200, 1650, 280, 50)]:
        dd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT_SOFT + (a,))
    deco = deco.filter(ImageFilter.GaussianBlur(30))
    img.paste(deco, (0, 0), deco)
    return img


def center_text(d, y, text, f, fill, spacing=18):
    for line in text.split("\n"):
        bbox = d.textbbox((0, 0), line, font=f)
        tw = bbox[2] - bbox[0]
        d.text(((W - tw) / 2 - bbox[0], y), line, font=f, fill=fill)
        y += (bbox[3] - bbox[1]) + spacing
    return y


def fit_font(d, text, path, max_w, start):
    size = start
    while size > 30:
        f = font(path, size)
        if d.textbbox((0, 0), text, font=f)[2] <= max_w:
            return f
        size -= 4
    return font(path, size)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for ch in text:
        # 句読点・閉じ括弧は行頭に来ないよう前の行に残す（禁則処理）
        if d.textbbox((0, 0), cur + ch, font=f)[2] > max_w and cur and ch not in "、。！？」』）":
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def subtitle(img, text):
    """画面下部に字幕（ナレーション）を表示。"""
    d = ImageDraw.Draw(img, "RGBA")
    f = font(BOLD, 46)
    lines = wrap(d, text, f, W - 180)
    lh = 66
    box_h = lh * len(lines) + 60
    top = H - 330 - box_h
    d.rounded_rectangle([60, top, W - 60, top + box_h], radius=36, fill=(255, 255, 255, 225),
                        outline=METAN + (255,), width=5)
    # 話者ラベル
    lf = font(BOLD, 34)
    label = "四国めたん"
    lb = d.textbbox((0, 0), label, font=lf)
    lw = lb[2] - lb[0] + 48
    d.rounded_rectangle([100, top - 30, 100 + lw, top + 30], radius=30, fill=METAN + (255,))
    d.text((124, top - 30 + (60 - (lb[3] - lb[1])) / 2 - lb[1]), label, font=lf, fill="white")
    y = top + 34
    for line in lines:
        bb = d.textbbox((0, 0), line, font=f)
        d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], y), line, font=f, fill=INK)
        y += lh


def credit(img):
    d = ImageDraw.Draw(img)
    f = font(MED, 30)
    text = "VOICEVOX:四国めたん"
    bb = d.textbbox((0, 0), text, font=f)
    d.text((W - 50 - (bb[2] - bb[0]), H - 120), text, font=f, fill=(90, 110, 100))
    f2 = font(MED, 26)
    note = "※口コミ等の一般的な評判に基づく。順位ではありません"
    bb = d.textbbox((0, 0), note, font=f2)
    d.text(((W - (bb[2] - bb[0])) / 2, H - 70), note, font=f2, fill=(120, 135, 128))


def header(d):
    f = font(BOLD, 48)
    d.rounded_rectangle([60, 110, W - 60, 230], radius=60, fill=ACCENT)
    center_text(d, 140, "穏やかな人が多い企業10選", f, "white")


def progress(d, idx):
    n = len(COMPANIES)
    gap = 70
    x0 = (W - gap * (n - 1)) / 2
    for i in range(n):
        cx, cy = x0 + i * gap, 290
        r = 14 if i == idx else 10
        fill = ACCENT if i <= idx else (205, 215, 210)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


# ---------- シーン ----------
def scene_intro(narr):
    img = background()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([140, 380, W - 140, 470], radius=45, fill=METAN)
    center_text(d, 398, "就活・転職の参考に", font(BOLD, 44), "white")
    y = center_text(d, 560, TITLE[0], font(BOLD, 100), INK)
    y = center_text(d, y + 10, TITLE[1].replace("10選", ""), font(BOLD, 88), INK)
    center_text(d, y + 20, "10選", font(BOLD, 240), ACCENT)
    subtitle(img, narr)
    credit(img)
    return img


def scene_company(i, name, tag, reason, narr):
    img = background()
    d = ImageDraw.Draw(img)
    header(d)
    progress(d, i)
    # カード
    card = [70, 360, W - 70, 1190]
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([c + o for c, o in zip(card, (0, 14, 0, 14))],
                                             radius=50, fill=(40, 70, 60, 50))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img.paste(shadow, (0, 0), shadow)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(card, radius=50, fill="white")
    # 番号バッジ
    cx, cy, r = W // 2, 500, 95
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
    nf = font(BOLD, 110)
    num = str(i + 1)
    bb = d.textbbox((0, 0), num, font=nf)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), num, font=nf, fill="white")
    # 業界タグ
    tf = font(BOLD, 38)
    bb = d.textbbox((0, 0), tag, font=tf)
    tw = bb[2] - bb[0] + 60
    d.rounded_rectangle([(W - tw) / 2, 630, (W + tw) / 2, 690], radius=30, fill=ACCENT_SOFT)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], 660 - (bb[3] - bb[1]) / 2 - bb[1]), tag, font=tf, fill=ACCENT)
    # 社名
    f = fit_font(d, name, BOLD, W - 220, 120)
    center_text(d, 730, name, f, INK)
    # 区切り線
    d.line([(W / 2 - 80, 900), (W / 2 + 80, 900)], fill=ACCENT, width=6)
    # 理由
    center_text(d, 950, reason, font(BOLD, 52), (70, 90, 82), spacing=26)
    subtitle(img, narr)
    credit(img)
    return img


def scene_outro(narr):
    img = background()
    d = ImageDraw.Draw(img)
    header(d)
    y = 420
    y = center_text(d, y, OUTRO_LINES[0], font(BOLD, 56), METAN) + 60
    y = center_text(d, y, OUTRO_LINES[1], font(BOLD, 64), INK) + 10
    center_text(d, y, OUTRO_LINES[2], font(BOLD, 90), ACCENT)
    subtitle(img, narr)
    credit(img)
    return img


# ---------- 書き出し ----------
def render_segment(png: Path, wav: Path, dur: float, out: Path):
    fade = 0.18
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", str(png),
        "-i", str(wav),
        "-filter_complex",
        f"[0:v]scale={W}:{H},format=yuv420p,"
        f"fade=t=in:st=0:d={fade},"
        f"zoompan=z='min(1+0.0004*on,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}[v];"
        f"[1:a]apad,atrim=0:{dur:.3f},aresample=48000[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(out),
    ], check=True)


def main():
    BUILD.mkdir(exist_ok=True)
    scenes = [("00_intro", scene_intro, (INTRO_NARR,), INTRO_NARR)]
    for i, (name, tag, reason, narr) in enumerate(COMPANIES):
        scenes.append((f"{i + 1:02d}_co", scene_company, (i, name, tag, reason, narr), narr))
    scenes.append(("99_outro", scene_outro, (OUTRO_NARR,), OUTRO_NARR))

    # 字幕はナレーション読み（カナ）ではなく表示用の表記にする
    display_fix = {"エヌティーティーデータ": "NTTデータ", "にっぽんゆうせん": "日本郵船",
                   "にっぽん政策投資銀行": "日本政策投資銀行", "オービー訪問": "OB訪問"}

    segs, total = [], 0.0
    for key, fn, args, narr in scenes:
        wav = BUILD / f"{key}.wav"
        dur = tts(narr, wav) + 0.1
        shown = narr
        for k, v in display_fix.items():
            shown = shown.replace(k, v)
        args = args[:-1] + (shown,)
        png = BUILD / f"{key}.png"
        fn(*args).save(png)
        seg = BUILD / f"{key}.mp4"
        render_segment(png, wav, dur, seg)
        segs.append(seg)
        total += dur
        print(f"{key}: {dur:.2f}s")

    lst = BUILD / "concat.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    out = HERE / "calm_companies_short.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    print(f"total {total:.1f}s -> {out}")


if __name__ == "__main__":
    main()
