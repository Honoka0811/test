"""timeline.json と narration.json から日本語字幕 (SRT) を生成する。

各シーンの文を「。」で区切り、ナレーション時間を文字数比で配分してキューにする。
  python subtitles.py   # → drone_short.ja.srt
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent


def ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    timeline = json.loads((HERE / "timeline.json").read_text(encoding="utf-8"))
    spec = json.loads((HERE / "narration.json").read_text(encoding="utf-8"))
    durations = json.loads((HERE / "audio" / "durations.json").read_text(encoding="utf-8"))
    text_by_id = {s["id"]: s["text"] for s in spec["scenes"]}

    cues = []
    for scene in timeline["scenes"]:
        sid = scene["id"]
        parts = [p for p in re.split(r"(?<=。)", text_by_id[sid]) if p.strip()]
        total_chars = sum(len(p) for p in parts)
        t = scene["voice_at"]
        speech = durations[sid]
        for p in parts:
            d = speech * len(p) / total_chars
            cues.append((t, min(t + d, scene["end"]), p.strip()))
            t += d

    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{ts(a)} --> {ts(b)}", text, ""]
    out = HERE / "drone_short.ja.srt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("srt:", out, f"{len(cues)} cues")


if __name__ == "__main__":
    main()
