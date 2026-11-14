# -*- coding: utf-8 -*-
"""ナレーション + BGM + 効果音をミックスして build/mix.wav を作る。

- BGM はナレーション中に自動で下げる(ダッキング)
- 効果音は build/plan.json(映像と同じキュー)の時刻に置くので、絵と音がフレーム単位で合う
使い方: python3 mix.py
"""
import json, os, wave
import numpy as np
import sfx
import bgm as bgm_mod

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000


def read_wav(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR, path
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x.reshape(-1, w.getnchannels())


def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def voice_chain(x):
    """ナレーションの整音: 70Hz 以下を切り、2.5kHz 以上を少し持ち上げ(スマホで聞き取りやすく)、軽くコンプ。"""
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    hp = 1 / np.sqrt(1 + (70 / np.maximum(f, 1)) ** 6)
    shelf = 1 + (10 ** (4.0 / 20) - 1) / (1 + (2500 / np.maximum(f, 1)) ** 2)
    body = 1 - 0.18 * np.exp(-0.5 * ((np.log2(np.maximum(f, 1) / 260)) / 0.6) ** 2)     # 260Hz 付近のこもりを少し抑える
    x = np.fft.irfft(spec * hp * shelf * body, n)
    # コンプレッサー(50ms RMS、しきい値 -22dB、比 2.5:1、メイクアップあり)
    hop = SR // 200
    r = np.sqrt(np.mean(x[:n // hop * hop].reshape(-1, hop) ** 2, axis=1)) + 1e-9
    k = 10
    r = np.convolve(np.pad(r, (k, k), mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), mode='valid')
    db = 20 * np.log10(r)
    gain_db = np.where(db > -22, (-22 + (db - -22) / 2.5) - db, 0.0)
    g = np.interp(np.arange(n), np.arange(len(gain_db)) * hop + hop / 2, 10 ** (gain_db / 20))
    return (x * g).astype(np.float32)


def band_db(x, lo=300, hi=4000):
    """声の明瞭度に効く帯域(300Hz〜4kHz)の RMS。"""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    return rms_db(np.fft.irfft(spec, len(x)))


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def main():
    plan = json.load(open(os.path.join(HERE, 'build', 'plan.json'), encoding='utf-8'))
    n = int(round(plan['duration'] * SR))
    voice = read_wav(os.path.join(HERE, 'build', 'narration.wav'))[:, 0]
    voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    voice = voice_chain(voice)

    # --- 効果音
    fx = np.zeros((n, 2), np.float32)
    MAKE = {
        'impact': lambda e: sfx.impact(), 'hit': lambda e: sfx.hit(), 'tick': lambda e: sfx.ding(2093, 0.35),
        'whoosh': lambda e: sfx.whoosh(seed=int(e['t'] * 10) % 7 + 1, pan_from=-0.6 if int(e['t']) % 2 else 0.6, pan_to=0.6 if int(e['t']) % 2 else -0.6),
        'pop': lambda e: sfx.pop(e.get('f', 660)), 'buzz': lambda e: sfx.buzz(), 'riser': lambda e: sfx.riser(e.get('dur', 1.6)),
        'subdrop': lambda e: sfx.sub_drop(), 'ding': lambda e: sfx.ding(1318.5, 1.4), 'sparkle': lambda e: sfx.sparkle(),
    }
    GAIN = {'impact': 0.85, 'hit': 0.5, 'tick': 0.16, 'whoosh': 0.20, 'pop': 0.28, 'buzz': 0.22, 'riser': 0.30, 'subdrop': 0.6, 'ding': 0.26, 'sparkle': 0.2}
    for e in plan['sfx']:
        sfx.place(fx, e['t'], MAKE[e['name']](e), GAIN[e['name']] * e.get('gain', 1.0))

    # --- BGM(ナレーションの包絡でダッキング)
    music = bgm_mod.generate(plan)
    music = np.pad(music, ((0, max(0, n - len(music))), (0, 0)))[:n]
    hop = SR // 100
    rms = np.sqrt(np.mean(voice[:n // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(rms)
    for i, v in enumerate(rms):
        prev = env[i - 1] if i else 0.0
        env[i] = max(v, prev * 0.965)            # リリース約 0.3 秒
    env = np.pad(np.repeat(env, hop), (0, n))[:n]
    speech = np.clip(env / 0.05, 0, 1)
    k = SR // 12
    speech = np.convolve(speech, np.ones(k) / k, mode='same')
    BGM_OPEN, BGM_SPEECH = 0.58, 0.145            # 無音時 / 発話時の BGM ゲイン
    music = music * (BGM_OPEN - (BGM_OPEN - BGM_SPEECH) * speech)[:, None]

    v = voice / (np.max(np.abs(voice)) + 1e-9) * 0.9
    mix = np.stack([v, v], axis=1) + music + fx
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / max(1.0, peak) * 1.15) / np.tanh(1.15) * 0.97   # 軽いソフトクリップ
    write_wav(os.path.join(HERE, 'build', 'mix.wav'), mix)
    write_wav(os.path.join(HERE, 'build', 'bgm.wav'), music)
    write_wav(os.path.join(HERE, 'build', 'sfx.wav'), fx)
    sp = speech > 0.5
    print(f'wrote build/mix.wav  {n / SR:.2f}s  peak {peak:.2f}')
    print(f'  発話区間: 声 {rms_db(v[sp]):.1f} dB / BGM {rms_db(music[sp].mean(1)):.1f} dB / 差 {rms_db(v[sp]) - rms_db(music[sp].mean(1)):.1f} dB')
    print(f'  無音区間: BGM {rms_db(music[~sp].mean(1)):.1f} dB')
    vm, mm = v * sp, music.mean(1) * sp
    print(f'  明瞭度帯域(300Hz-4kHz)での声と BGM の差: {band_db(vm) - band_db(mm):.1f} dB(10dB 以上が目安)')


if __name__ == '__main__':
    main()
