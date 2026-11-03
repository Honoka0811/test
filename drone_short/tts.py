"""narration.json の各シーン文を VOICEVOX（青山龍星）で合成し、WAV と長さ一覧 durations.json を出力する。

2つのバックエンドに対応:
  A) VOICEVOX エンジン HTTP API（VOICEVOX アプリを起動しておけば localhost:50021 で使える）
     python tts.py --engine http://127.0.0.1:50021 --out audio
  B) VOICEVOX CORE（Python バインディング voicevox_core が入っている場合）
     python tts.py --onnxruntime <libonnxruntime.so> --dict <open_jtalk 辞書 dir> --vvm <15.vvm> --out audio
"""
import argparse
import json
import pathlib
import urllib.parse
import urllib.request
import wave

HERE = pathlib.Path(__file__).resolve().parent


def synth_engine(base: str, text: str, style_id: int, speed: float) -> bytes:
    q = urllib.parse.urlencode({"text": text, "speaker": style_id})
    req = urllib.request.Request(f"{base}/audio_query?{q}", method="POST")
    with urllib.request.urlopen(req) as r:
        query = json.load(r)
    query["speedScale"] = speed
    query["postPhonemeLength"] = 0.2
    req = urllib.request.Request(
        f"{base}/synthesis?speaker={style_id}",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return r.read()


def make_core_synth(onnxruntime: str, dict_dir: str, vvm: str, style_id: int):
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

    ort = Onnxruntime.load_once(filename=onnxruntime)
    synth = Synthesizer(ort, OpenJtalk(dict_dir))
    with VoiceModelFile.open(vvm) as model:
        synth.load_voice_model(model)
        speaker = [c.name for c in model.metas if any(s.id == style_id for s in c.styles)]
    print("speaker:", speaker)

    def run(text: str, speed: float) -> bytes:
        query = synth.create_audio_query(text, style_id)
        query.speed_scale = speed
        query.post_phoneme_length = 0.2
        return synth.synthesis(query, style_id)

    return run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", help="VOICEVOX エンジンの URL (例 http://127.0.0.1:50021)")
    ap.add_argument("--onnxruntime")
    ap.add_argument("--dict")
    ap.add_argument("--vvm")
    ap.add_argument("--out", default=str(HERE / "audio"))
    ap.add_argument("--narration", default=str(HERE / "narration.json"))
    args = ap.parse_args()

    spec = json.loads(pathlib.Path(args.narration).read_text(encoding="utf-8"))
    style_id, speed = spec["style_id"], spec.get("speed_scale", 1.0)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.engine:
        run = lambda text, spd: synth_engine(args.engine.rstrip("/"), text, style_id, spd)
    elif args.onnxruntime and args.dict and args.vvm:
        run = make_core_synth(args.onnxruntime, args.dict, args.vvm, style_id)
    else:
        ap.error("--engine か、--onnxruntime/--dict/--vvm の組を指定してください")

    durations = {}
    for scene in spec["scenes"]:
        wav = run(scene["text"], speed)
        path = out / f'{scene["id"]}.wav'
        path.write_bytes(wav)
        with wave.open(str(path)) as w:
            dur = w.getnframes() / w.getframerate()
        durations[scene["id"]] = round(dur, 3)
        print(f'{scene["id"]}: {dur:5.2f}s  {scene["text"][:28]}…')

    (out / "durations.json").write_text(json.dumps(durations, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total speech:", round(sum(durations.values()), 1), "s")


if __name__ == "__main__":
    main()
