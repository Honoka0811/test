"""ナレーション WAV の長さに合わせてシーン尺を決め、動画を再描画し、ナレーションと BGM を重ねて最終 MP4 を出力する。

前提: tts.py で audio/<scene>.wav と audio/durations.json ができていること。
  python assemble.py                # → drone_short_voiced.mp4（映像の再描画込み）
  python assemble.py --audio-only   # 映像は前回の drone_short_silent.mp4 を再利用し、音声だけ作り直す
  python assemble.py --no-bgm       # BGM なし
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
AUDIO = HERE / "audio"
LEAD = 0.45   # シーン開始からナレーション開始までの間
TAIL = 0.7    # ナレーション終了からシーン終了までの間

# 無音版と同じ最低尺（ナレーションが短くてもこれ以上は維持する）
MIN_DUR = {"s0": 4.0, "s1": 5.5, "s2": 6.0, "s3": 6.0, "s4": 6.0, "s5": 6.0, "s6": 6.0, "s7": 6.0, "s8": 7.0, "s9": 6.0}


def main() -> None:
    durations = json.loads((AUDIO / "durations.json").read_text(encoding="utf-8"))
    scenes, t = [], 0.0
    for sid, min_dur in MIN_DUR.items():
        dur = max(min_dur, LEAD + durations[sid] + TAIL)
        scenes.append({"id": sid, "start": round(t, 3), "end": round(t + dur, 3), "voice_at": round(t + LEAD, 3)})
        t += dur
    timeline = {"duration": round(t, 3), "scenes": scenes}
    (HERE / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print("timeline:", {s["id"]: (s["start"], s["end"]) for s in scenes}, "total", timeline["duration"])

    silent = HERE / "drone_short_silent.mp4"
    if "--audio-only" in sys.argv and silent.exists():
        print("reuse:", silent)
    else:
        subprocess.run(["node", str(HERE / "render.cjs"), "--timeline", str(HERE / "timeline.json"), "--out", str(silent)], check=True)

    # 各 WAV をシーン開始位置に置いて1本の音声にまとめる
    inputs, filters, labels = [], [], []
    for i, s in enumerate(scenes):
        inputs += ["-i", str(AUDIO / f'{s["id"]}.wav')]
        ms = int(s["voice_at"] * 1000)
        filters.append(f"[{i}]adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    n = len(scenes)
    filters.append(f'{"".join(labels)}amix=inputs={n}:normalize=0:dropout_transition=0,apad=whole_dur={timeline["duration"]}[mix]')
    narration = HERE / "narration.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[mix]", "-t", str(timeline["duration"]), str(narration)], check=True)

    # BGM を生成し、ナレーション中は自動で音量を下げて(ダッキング)混ぜる
    mixed = narration
    if "--no-bgm" not in sys.argv:
        bgm = HERE / "bgm.wav"
        subprocess.run([sys.executable, str(HERE / "bgm.py"), str(timeline["duration"]), str(bgm)], check=True)
        mixed = HERE / "mix.wav"
        graph = (
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[nar][sc];"
            "[1:a]volume=0.55[bg];"
            "[bg][sc]sidechaincompress=threshold=0.015:ratio=8:attack=40:release=700:makeup=1[bgd];"
            "[nar][bgd]amix=inputs=2:normalize=0,alimiter=limit=0.95[mix]"
        )
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(narration), "-i", str(bgm),
                        "-filter_complex", graph, "-map", "[mix]", str(mixed)], check=True)

    final = HERE / "drone_short_voiced.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(mixed),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    print("done:", final)


if __name__ == "__main__":
    main()
