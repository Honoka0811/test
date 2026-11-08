#!/usr/bin/env python3
"""YouTubeショート生成: 「日本の新興宗教 信者数ランキングTOP5」(紹介系)
VOICEVOX(四国めたん)合成 → ASS字幕 → ダークBGM生成(numpy) → ffmpeg合成

必要アセット(環境変数):
  VVX_ORT / VVX_DICT / VVX_VVM / FONTS_DIR  (詳細は yt-shorts-cult-psychology/README.md)
"""
import os, sys, wave, subprocess, math
import numpy as np

OUT = os.environ.get("OUT_DIR", os.path.dirname(os.path.abspath(__file__)) + "/out")
ORT = os.environ["VVX_ORT"]
DICT = os.environ["VVX_DICT"]
VVM = os.environ["VVX_VVM"]
FONTS = os.environ.get("FONTS_DIR", os.path.expanduser("~/.fonts"))
os.makedirs(OUT, exist_ok=True)

NORMAL, HISOHISO = 2, 37  # 四国めたん スタイルID

RED = r"{\c&H303BFF&}"    # #FF3B30
GOLD = r"{\c&H0AD6FF&}"   # #FFD60A
WHT = r"{\c&HFFFFFF&}"
BIG = r"{\fs170}"         # 順位バッジ用特大

# (tts_text, style_id, speed, post_pause_sec, [(caption, weight), ...])
SCENES = [
    ("日本でいちばん信者が多い新興宗教……知ってる？", HISOHISO, 0.95, 0.45,
     [(r"日本で一番\N信者が多い\N新興宗教…\N知ってる？", 1)]),
    ("公称の信者数で、日本の新興宗教ランキング、トップ５。", NORMAL, 1.1, 0.35,
     [(r"信者数ランキング\N" + GOLD + r"TOP5", 1)]),
    ("第５位、真如苑。１９３６年にできた仏教系の教団で、約９２万人。", NORMAL, 1.1, 0.4,
     [(BIG + RED + r"第5位", 22),
      (r"真如苑\N仏教系・1936年", 42),
      (GOLD + r"約92万人", 36)]),
    ("第４位、天理教。江戸時代の終わりに生まれた、新宗教の草分け。約１１０万人。", NORMAL, 1.1, 0.4,
     [(BIG + RED + r"第4位", 20),
      (r"天理教\N幕末創立の草分け", 46),
      (GOLD + r"約110万人", 34)]),
    ("第３位、霊友会。大正時代にできた法華系の教団。約１２０万人。", NORMAL, 1.1, 0.4,
     [(BIG + RED + r"第3位", 22),
      (r"霊友会\N法華系・大正時代", 44),
      (GOLD + r"約120万人", 34)]),
    ("第２位、立正佼成会。霊友会から分かれて、約２００万人。", NORMAL, 1.1, 0.4,
     [(BIG + RED + r"第2位", 24),
      (r"立正佼成会\N霊友会から分派", 42),
      (GOLD + r"約200万人", 34)]),
    ("そして、第１位は……。", HISOHISO, 0.9, 0.7,
     [(r"そして\N第1位は……", 1)]),
    ("創価学会。公称、８２７万世帯。日本最大の新宗教だよ。", NORMAL, 1.1, 0.45,
     [(BIG + RED + r"第1位", 18),
      (r"創価学会", 28),
      (GOLD + r"公称827万世帯" + WHT + r"\N日本最大", 54)]),
    ("ただし、この数字はぜんぶ、各団体の自己申告。実際に活動している人は、ずっと少ないとも言われてるよ。", NORMAL, 1.1, 0.4,
     [(r"ただし数字は全部\N" + RED + r"自己申告", 45),
      (r"実際の活動者は\N" + GOLD + r"ずっと少ない" + WHT + r"とも", 55)]),
    ("気になる団体があったら、コメントで教えてね。次の動画で深掘りするよ。", NORMAL, 1.15, 0.2,
     [(r"気になる団体は\N" + GOLD + r"コメントへ", 52),
      (r"次回\N深掘りします", 48)]),
]

RANK_SCENES = (2, 3, 4, 5, 7)   # 低音インパクトを置くシーン
RISER_SCENE = 6                 # この間ノイズライザー→次シーン頭で最大ブーム

# ---------- 1. 音声合成 ----------
def synthesize():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort = Onnxruntime.load_once(filename=ORT)
    synth = Synthesizer(ort, OpenJtalk(DICT))
    for f in ("0.vvm", "5.vvm"):
        with VoiceModelFile.open(os.path.join(VVM, f)) as m:
            synth.load_voice_model(m)
    sr = 24000
    pcm_all = bytearray()
    times = []
    t = 0.35
    pcm_all += b"\x00\x00" * int(sr * t)
    for text, style, speed, pause, _caps in SCENES:
        q = synth.create_audio_query(text, style)
        q.speed_scale = speed
        q.post_phoneme_length = 0.08
        q.pre_phoneme_length = 0.06
        wav_bytes = synth.synthesis(q, style)
        tmp = os.path.join(OUT, "_tmp.wav")
        with open(tmp, "wb") as f:
            f.write(wav_bytes)
        with wave.open(tmp) as wf:
            assert wf.getframerate() == sr and wf.getnchannels() == 1
            frames = wf.readframes(wf.getnframes())
        dur = len(frames) / 2 / sr
        times.append((t, t + dur))
        pcm_all += frames
        pcm_all += b"\x00\x00" * int(sr * pause)
        t += dur + pause
    total = len(pcm_all) / 2 / sr + 0.7
    pcm_all += b"\x00\x00" * int(sr * 0.7)
    with wave.open(os.path.join(OUT, "voice.wav"), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(bytes(pcm_all))
    os.remove(os.path.join(OUT, "_tmp.wav"))
    return times, total

# ---------- 2. ASS字幕 ----------
def ass_time(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(times, total):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Noto Sans CJK JP Black,112,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,12,6,5,40,40,40,1
Style: Whisper,Noto Sans CJK JP Black,100,&H00E8E8F2,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,2,0,1,10,5,5,40,40,40,1
Style: Title,Noto Sans CJK JP Black,58,&H000AD6FF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,1,0,1,8,3,5,40,40,40,1
Style: Note,Noto Sans CJK JP,30,&H009A9A9A,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,40,40,100,1
Style: Credit,Noto Sans CJK JP,34,&H00B8B8B8,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,2,40,40,46,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,,0,0,0,,{{\\pos(540,300)\\fad(300,300)}}日本の新興宗教 信者数TOP5")
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Note,,0,0,0,,※信者数は各団体の公称値")
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Credit,,0,0,0,,VOICEVOX:四国めたん")
    pop = r"{\fad(110,90)\fscx93\fscy93\t(0,130,\fscx100\fscy100)}"
    slam = r"{\fad(60,80)\fscx132\fscy132\t(0,110,\fscx100\fscy100)}"  # 順位バッジ: 大→縮むスラム
    whis = r"{\fad(260,200)\blur2.2}"
    for (st, en), (text, style, speed, pause, caps) in zip(times, SCENES):
        seg_total = en - st + (pause * 0.85)
        wsum = sum(w for _, w in caps)
        cur = st
        for j, (cap, wgt) in enumerate(caps):
            d = seg_total * wgt / wsum
            sty = "Whisper" if style == HISOHISO else "Main"
            if style == HISOHISO:
                fx = whis
            elif j == 0 and cap.startswith(BIG):
                fx = slam
            else:
                fx = pop
            ev.append(f"Dialogue: 1,{ass_time(cur)},{ass_time(cur + d)},{sty},,0,0,0,,{{\\pos(540,1170)}}{fx}{cap}")
            cur += d
    with open(os.path.join(OUT, "subs.ass"), "w", encoding="utf-8") as f:
        f.write(header + "\n".join(ev) + "\n")

# ---------- 3. BGM生成 ----------
def build_bgm(times, total):
    sr = 44100
    n = int(sr * total)
    t = np.arange(n) / sr
    mix = np.zeros(n)
    rng = np.random.default_rng(7)

    # ダークパッド (Aマイナー低域)
    for f0, amp in [(55, .30), (82.41, .22), (110, .20), (130.81, .14)]:
        vib = f0 * (1 + 0.0035 * np.sin(2 * np.pi * 0.13 * t + f0))
        pad = np.sin(2 * np.pi * vib * t) + 0.35 * np.sin(2 * np.pi * 2 * f0 * t + 1.3)
        lfo = 0.68 + 0.32 * np.sin(2 * np.pi * 0.07 * t + f0 * 0.5)
        mix += amp * pad * lfo
    mix *= 0.16

    # 心音 (72BPM)
    beat = 60 / 72
    def thump(center, strength):
        i0 = int(center * sr); dur = int(0.16 * sr)
        if i0 < 0 or i0 + dur > n: return
        tt = np.arange(dur) / sr
        env = np.exp(-tt * 26)
        freq = 58 * np.exp(-tt * 7) + 36
        mix[i0:i0 + dur] += strength * env * np.sin(2 * np.pi * np.cumsum(freq) / sr)
    k = 0.0
    while k < total:
        grow = 0.5 + 0.5 * min(1.0, k / total * 1.4)
        thump(k, 0.50 * grow)
        thump(k + 0.30, 0.34 * grow)
        k += beat

    # 秒針 (第5位の発表から)
    tick_start = times[2][0] if len(times) > 2 else total * 0.2
    k = math.ceil(tick_start)
    while k < total - 1:
        i0 = int(k * sr); dur = int(0.02 * sr)
        tt = np.arange(dur) / sr
        mix[i0:i0 + dur] += 0.10 * rng.standard_normal(dur) * np.exp(-tt * 300)
        k += 1.0

    # 順位発表インパクト
    def boom(at, strength):
        i0 = int(max(0, at - 0.05) * sr); dur = int(1.1 * sr)
        if i0 + dur > n: dur = n - i0
        tt = np.arange(dur) / sr
        env = np.exp(-tt * 4.5)
        b = np.sin(2 * np.pi * (44 * np.exp(-tt * 2.5) + 30) * tt)
        nz = rng.standard_normal(dur) * np.exp(-tt * 18) * 0.25
        mix[i0:i0 + dur] += strength * env * b + nz * strength / 0.55
    for idx in RANK_SCENES:
        if idx < len(times):
            boom(times[idx][0], 0.75 if idx == 7 else 0.5)

    # 第1位前のノイズライザー (「そして第1位は……」の間)
    if RISER_SCENE < len(times) and RISER_SCENE + 1 < len(times):
        r0 = times[RISER_SCENE][0]
        r1 = times[RISER_SCENE + 1][0]
        i0, i1 = int(r0 * sr), int(r1 * sr)
        dur = i1 - i0
        if dur > 0:
            tt = np.linspace(0, 1, dur)
            riser = rng.standard_normal(dur)
            # 簡易ハイパス気味: 隣接差分
            riser = np.diff(riser, prepend=0.0)
            mix[i0:i1] += riser * (tt ** 2.2) * 0.22

    fi, fo = int(0.8 * sr), int(1.6 * sr)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)

    mix = np.tanh(mix * 1.2) * 0.85
    stereo = np.stack([mix, np.roll(mix, int(0.0008 * sr))], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, "bgm.wav"), "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

# ---------- 4. ffmpeg合成 ----------
def render(total):
    out_mp4 = os.path.join(OUT, "shorts_shinshukyo_ranking.mp4")
    vf = (
        "[0:v]noise=alls=5:allf=t,vignette=PI/4.2,"
        "eq=eval=frame:brightness='0.018*sin(2*PI*t*0.65)':saturation=1.12,"
        f"subtitles={OUT}/subs.ass:fontsdir={FONTS}[v];"
        "[1:a]aresample=44100,aformat=channel_layouts=stereo,loudnorm=I=-15:TP=-1.5,asplit=2[vo1][vo2];"
        "[2:a]volume=0.85[bgsrc];"
        "[bgsrc][vo1]sidechaincompress=threshold=0.04:ratio=12:attack=12:release=420[bg];"
        "[vo2][bg]amix=inputs=2:normalize=0:duration=first,"
        "loudnorm=I=-14:TP=-1.2:LRA=11,alimiter=limit=0.95[aout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"gradients=s=1080x1920:d={total:.2f}:r=30:c0=0x3A0016:c1=0x06000C:"
              "x0=540:y0=520:x1=560:y1=1960:speed=0.015",
        "-i", os.path.join(OUT, "voice.wav"),
        "-i", os.path.join(OUT, "bgm.wav"),
        "-filter_complex", vf,
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-crf", "26", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total:.2f}", "-movflags", "+faststart",
        out_mp4,
    ]
    subprocess.run(cmd, check=True)
    return out_mp4

if __name__ == "__main__":
    print("1/4 音声合成中 (VOICEVOX:四国めたん)...")
    times, total = synthesize()
    print(f"   合計 {total:.1f} 秒")
    if total > 60.5:
        print("   警告: 60秒を超過。speedを上げるか台本を短縮してください。", file=sys.stderr)
    print("2/4 字幕生成中...")
    build_ass(times, total)
    print("3/4 BGM生成中...")
    build_bgm(times, total)
    print("4/4 動画レンダリング中...")
    path = render(total)
    print("完成:", path)
