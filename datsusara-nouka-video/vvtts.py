# -*- coding: utf-8 -*-
"""VOICEVOX core (offline) narration helper.
Requires: pip install voicevox_core wheel, VOICEVOX ONNX Runtime and .vvm models.
Set VV_DIR to a directory containing ort/lib/libvoicevox_onnxruntime.so* and models/*.vvm.
"""
import glob, io, os, wave
import numpy as np

VOICES = {  # name -> (style_id, credit)
    "metan": (2, "VOICEVOX:四国めたん"), "zundamon": (3, "VOICEVOX:ずんだもん"), "tsumugi": (8, "VOICEVOX:春日部つむぎ"),
    "himari": (14, "VOICEVOX:冥鳴ひまり"), "sora": (16, "VOICEVOX:九州そら"), "no7": (31, "VOICEVOX:No.7"),
    "kiritan": (108, "VOICEVOX:東北きりたん"), "mochiko": (20, "VOICEVOX:もち子さん"),
}

class VoicevoxTTS:
    def __init__(self, vv_dir=None):
        import pyopenjtalk
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        vv_dir = vv_dir or os.environ.get("VV_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "vv"))
        so = sorted(glob.glob(os.path.join(vv_dir, "ort", "lib", "libvoicevox_onnxruntime.so.*")))[-1]
        dic = glob.glob(os.path.join(os.path.dirname(pyopenjtalk.__file__), "open_jtalk_dic_utf_8-*"))[0]
        ort = Onnxruntime.load_once(filename=so)
        self.syn = Synthesizer(ort, OpenJtalk(dic))
        self._VoiceModelFile = VoiceModelFile
        self.vv_dir = vv_dir
        self.loaded = set()
        self.sr = 24000

    def ensure_style(self, style_id):
        if style_id in self.loaded:
            return
        for p in glob.glob(os.path.join(self.vv_dir, "models", "*.vvm")):
            with self._VoiceModelFile.open(p) as m:
                if any(s.id == style_id for c in m.metas for s in c.styles):
                    self.syn.load_voice_model(m)
                    self.loaded.update(s.id for c in m.metas for s in c.styles)
                    return
        raise ValueError(f"style {style_id} not found")

    def tts(self, text, style_id, speed=1.0, pitch=0.0, intonation=1.0, pre=0.1, post=0.1):
        """Return float32 mono samples in [-1, 1] at self.sr."""
        self.ensure_style(style_id)
        q = self.syn.create_audio_query(text, style_id)
        q.speed_scale = speed; q.pitch_scale = pitch; q.intonation_scale = intonation
        q.pre_phoneme_length = pre; q.post_phoneme_length = post
        q.output_sampling_rate = self.sr
        wav = self.syn.synthesis(q, style_id)
        with wave.open(io.BytesIO(wav)) as f:
            assert f.getframerate() == self.sr and f.getsampwidth() == 2
            x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            if f.getnchannels() == 2:
                x = x.reshape(-1, 2).mean(axis=1)
        return x
