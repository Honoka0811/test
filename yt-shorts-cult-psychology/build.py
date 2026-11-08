#!/usr/bin/env python3
"""YouTubeショート生成パイプライン:
VOICEVOX(四国めたん)合成 → ASS字幕 → ダークBGM生成(numpy) → ffmpeg合成

必要アセット(環境変数で指定):
  VVX_ORT   : libvoicevox_onnxruntime.so のパス
  VVX_DICT  : open_jtalk_dic_utf_8-1.11 ディレクトリ
  VVX_VVM   : vvmファイルのあるディレクトリ (0.vvm, 5.vvm)
  FONTS_DIR : Noto Sans CJK JP Black/Bold を置いたディレクトリ
"""
import os, sys, wave, struct, subprocess, math
import numpy as np

OUT = os.environ.get("OUT_DIR", os.path.dirname(os.path.abspath(__file__)) + "/out")
ORT = os.environ["VVX_ORT"]
DICT = os.environ["VVX_DICT"]
VVM = os.environ["VVX_VVM"]
FONTS = os.environ.get("FONTS_DIR", os.path.expanduser("~/.fonts"))
os.makedirs(OUT, exist_ok=True)

NORMAL, HISOHISO = 2, 37  # 四国めたん スタイルID

W, Y_ACCENT = "", ""  # placeholders (colors live in ASS tags below)
RED = r"{\c&H303BFF&}"      # #FF3B30
GOLD = r"{\c&H0AD6FF&}"     # #FFD60A
WHT = r"{\c&HFFFFFF&}"

# (tts_text, style_id, speed, post_pause_sec, [(caption, weight), ...])
SCENES = [
    ("ねえ……知ってた？", HISOHISO, 0.95, 0.45,
     [(r"ねえ……\N知ってた？", 1)]),
    ("カルトの勧誘は、絶対に、宗教って名乗らないの。", NORMAL, 1.1, 0.3,
     [(r"カルトの勧誘は\N絶対に" + RED + r"「宗教」" + WHT + r"と\N名乗らない", 1)]),
    ("ヨガ教室。自己啓発セミナー。ボランティア。入り口はぜんぶ、普通の顔をしてるんだよ。", NORMAL, 1.1, 0.35,
     [(r"ヨガ教室\N自己啓発セミナー\Nボランティア", 48),
      (r"入り口は全部\N" + GOLD + r"普通の顔" + WHT + r"をしてる", 52)]),
    ("今日は、普通の人がハマっていく仕組みを、３つだけ教えるね。", NORMAL, 1.1, 0.4,
     [(r"ハマる仕組みを\N" + GOLD + r"３つ" + WHT + r"だけ教えるね", 1)]),
    ("１つ目。ラブボンビング。初対面なのに、全員があなたを褒めまくるの。孤独なときほど、これが効いちゃう。", NORMAL, 1.1, 0.35,
     [(RED + r"①ラブボンビング", 30),
      (r"初対面なのに\N全員が褒めまくる", 38),
      (GOLD + r"孤独なとき" + WHT + r"ほど\N効いてしまう", 32)]),
    ("２つ目。小さな要求から。最初は無料のお茶会。次は勉強会。気づいたときには、お布施と勧誘ノルマ。", NORMAL, 1.1, 0.35,
     [(RED + r"②小さな要求から", 26),
      (r"無料のお茶会\N→ 勉強会", 36),
      (r"気づけば\N" + GOLD + r"お布施とノルマ", 38)]),
    ("３つ目。サンクコスト。ここまでやったんだから。注ぎ込んだ時間とお金が、あなたを縛るの。", NORMAL, 1.1, 0.35,
     [(RED + r"③サンクコスト", 24),
      (r"「ここまで\Nやったんだから…」", 34),
      (r"時間とお金が\N" + GOLD + r"あなたを縛る", 42)]),
    ("狙われるのは、弱い人じゃない。真面目で、優しくて、ちょっと疲れてる人。", NORMAL, 1.1, 0.4,
     [(r"狙われるのは\N弱い人じゃない", 45),
      (r"真面目で優しくて\N" + GOLD + r"ちょっと疲れてる人", 55)]),
    ("……今の、あなたかも。", HISOHISO, 0.9, 0.6,
     [(r"……今の" + RED + r"あなた" + WHT + r"、かも", 1)]),
    ("身を守る方法は、コメント欄に固定しておくね。大切な人を守るために、シェアして。", NORMAL, 1.15, 0.2,
     [(r"守る方法は\N" + GOLD + r"コメント欄に固定" + WHT, 50),
      (r"大切な人に\Nシェアしてね", 50)]),
]

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
    times = []  # (start, end) per scene (voice only, no post pause)
    t = 0.35  # lead-in silence
    pcm_all += b"\x00\x00" * int(sr * t)
    for text, style, speed, pause, _caps in SCENES:
        q = synth.create_audio_query(text, style)
        q.speed_scale = speed
        q.post_phoneme_length = 0.08
        q.pre_phoneme_length = 0.06
        wav_bytes = synth.synthesis(q, style)
        with open(os.path.join(OUT, "_tmp.wav"), "wb") as f:
            f.write(wav_bytes)
        with wave.open(os.path.join(OUT, "_tmp.wav")) as wf:
            assert wf.getframerate() == sr and wf.getnchannels() == 1
            frames = wf.readframes(wf.getnframes())
        dur = len(frames) / 2 / sr
        times.append((t, t + dur))
        pcm_all += frames
        pcm_all += b"\x00\x00" * int(sr * pause)
        t += dur + pause
    total = len(pcm_all) / 2 / sr + 0.7  # tail
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
Style: Credit,Noto Sans CJK JP,34,&H00B8B8B8,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,2,40,40,46,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    # 常時表示: 上部タイトル & クレジット
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,,0,0,0,,{{\\pos(540,300)\\fad(300,300)}}【注意】カルト勧誘の手口")
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Credit,,0,0,0,,VOICEVOX:四国めたん")
    pop = r"{\fad(110,90)\fscx93\fscy93\t(0,130,\fscx100\fscy100)}"
    whis = r"{\fad(260,200)\blur2.2}"
    for i, ((st, en), (text, style, speed, pause, caps)) in enumerate(zip(times, SCENES)):
        seg_total = en - st + (pause * 0.85)  # 字幕はポーズ中も少し残す
        wsum = sum(w for _, w in caps)
        cur = st
        for cap, wgt in caps:
            d = seg_total * wgt / wsum
            sty = "Whisper" if style == HISOHISO else "Main"
            fx = whis if style == HISOHISO else pop
            ev.append(f"Dialogue: 1,{ass_time(cur)},{ass_time(cur + d)},{sty},,0,0,0,,{{\\pos(540,1170)}}{fx}{cap}")
            cur += d
    with open(os.path.join(OUT, "subs.ass"), "w", encoding="utf-8") as f:
        f.write(header + "\n".join(ev) + "\n")

# ---------- 3. BGM生成 (ダークアンビエント + 心音 + 秒針) ----------
def build_bgm(times, total):
    sr = 44100
    n = int(sr * total)
    t = np.arange(n) / sr
    mix = np.zeros(n)

    # ダークパッド: Aマイナーの低域クラスタ(55Hz=A1, 82.4=E2, 110=A2, 130.8=C3)
    for f0, amp in [(55, .30), (82.41, .22), (110, .20), (130.81, .14)]:
        vib = f0 * (1 + 0.0035 * np.sin(2 * np.pi * 0.13 * t + f0))
        pad = np.sin(2 * np.pi * vib * t) + 0.35 * np.sin(2 * np.pi * 2 * f0 * t + 1.3)
        lfo = 0.68 + 0.32 * np.sin(2 * np.pi * 0.07 * t + f0 * 0.5)
        mix += amp * pad * lfo
    mix *= 0.16

    # 心音 (72BPM, ドッ・ドッの2連)
    beat = 60 / 72
    def thump(center, strength):
        i0 = int(center * sr)
        dur = int(0.16 * sr)
        if i0 + dur > n: return
        tt = np.arange(dur) / sr
        env = np.exp(-tt * 26)
        freq = 58 * np.exp(-tt * 7) + 36
        mix[i0:i0 + dur] += strength * env * np.sin(2 * np.pi * np.cumsum(freq) / sr)
    k = 0.0
    while k < total:
        grow = 0.5 + 0.5 * min(1.0, k / total * 1.4)  # 後半ほど強く
        thump(k, 0.50 * grow)
        thump(k + 0.30, 0.34 * grow)
        k += beat

    # 秒針 (シーン4以降 = 手口解説パートから)
    tick_start = times[4][0] if len(times) > 4 else total * 0.3
    rng = np.random.default_rng(7)
    k = math.ceil(tick_start)
    while k < total - 1:
        i0 = int(k * sr)
        dur = int(0.02 * sr)
        tt = np.arange(dur) / sr
        mix[i0:i0 + dur] += 0.10 * rng.standard_normal(dur) * np.exp(-tt * 300)
        k += 1.0

    # シーン切替インパクト (①②③と「今のあなたかも」の頭)
    for idx in (4, 5, 6, 8):
        if idx >= len(times): continue
        i0 = int(max(0, times[idx][0] - 0.05) * sr)
        dur = int(1.1 * sr)
        if i0 + dur > n: dur = n - i0
        tt = np.arange(dur) / sr
        env = np.exp(-tt * 4.5)
        boom = np.sin(2 * np.pi * (44 * np.exp(-tt * 2.5) + 30) * tt)
        noise = rng.standard_normal(dur) * np.exp(-tt * 18) * 0.25
        mix[i0:i0 + dur] += 0.55 * env * boom + noise

    # フェードイン/アウト
    fi, fo = int(0.8 * sr), int(1.6 * sr)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)

    mix = np.tanh(mix * 1.2) * 0.85  # ソフトクリップ
    stereo = np.stack([mix, np.roll(mix, int(0.0008 * sr))], axis=1)  # 軽いハース効果
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, "bgm.wav"), "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

# ---------- 4. ffmpeg合成 ----------
def render(total):
    out_mp4 = os.path.join(OUT, "shorts_cult_psychology.mp4")
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
