"""BGMを合成し、narrate.py が出力したナレーションとミックスする。
使い方: python3 mix.py <作業ディレクトリ>  -> <作業ディレクトリ>/mix.wav
"""
import json, sys, subprocess

S = sys.argv[1]
tm = json.load(open(f"{S}/voice/timing.json"))
D = tm["duration"]
BEAT = 0.35  # 約171BPM
BAR = 1.4    # コードチェンジ間隔（4拍）
c = lambda a, b: f"if(lt(mod(t,{BAR*2}),{BAR}),{a},{b})"
E = (f"0.05*(sin(2*PI*{c(220,174.61)}*t)+sin(2*PI*{c(261.63,220)}*t)+sin(2*PI*{c(329.63,261.63)}*t))"
     f"*(0.7+0.3*sin(2*PI*0.5*t))"
     f"+0.4*sin(2*PI*55*t)*exp(-16*mod(t,{BEAT}))"
     f"+0.05*sin(2*PI*{c(659.25,523.25)}*t)*exp(-10*mod(t,{BEAT/2}))")
inputs = ["-f", "lavfi", "-t", str(D), "-i", f"aevalsrc='{E}':s=44100"]
fl = [f"[0]afade=t=in:d=0.1,afade=t=out:st={D-0.8}:d=0.8,lowpass=f=5000,volume=0.35,"
      f"aformat=channel_layouts=stereo[bgm]"]
for i, o in enumerate(tm["offsets"]):
    inputs += ["-i", f"{S}/voice/n{i}.wav"]
    ms = int(o * 1000)
    fl.append(f"[{i+1}]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume=1.6[v{i}]")
n = len(tm["offsets"])
fl.append("".join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0[voice]")
fl.append("[bgm][voice]amix=inputs=2:normalize=0,alimiter=limit=0.95[out]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fl),
                "-map", "[out]", "-t", str(D), f"{S}/mix.wav"], check=True)
