# -*- coding: utf-8 -*-
"""BGM を numpy だけで合成する(外部音源・生成AI音楽なし。完全オリジナルで権利表記不要)。

構成は build/plan.json のシーン時刻に合わせる:
  0 秒〜           : 鼓動するベースとキックで即スタート(イントロなし)
  公転〜           : アルペジオとハットが加わる
  「真犯人は…」    : ドラムを抜いて溜める
  銀河の判明       : ドロップ。パッドが広がりフルの厚み
  銀河 1 周〜      : ドラムを抜いて浮遊感(深い時間の話)。「同じ場所に…」でさらに静かに
  「見始めた場所」 : スネアロールで溜め、最後のフレームで切る → ループ再生で 0 秒のインパクトにつながる

1 小節 = ゴール時刻(56.13 秒)/ 28。動画はちょうど 28 小節で終わり、次の再生の頭が 1 小節目になる。
使い方: python3 bgm.py  → build/bgm.wav
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.05):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    return (e * np.clip((dur - t) / r, 0, 1)).astype(np.float32)


def saw(f, n, harm=10, bright=1.0, phase=0.0):
    """帯域制限のこぎり波(倍音を足し合わせる)。bright を下げると高域が丸くなる。"""
    t = np.arange(n) / SR
    x = np.zeros(n, dtype=np.float32)
    for h in range(1, harm + 1):
        if f * h > 9000:
            break
        x += (np.sin(2 * np.pi * f * h * t + phase * h) / h * np.exp(-(h - 1) * (1 - bright) * 0.5)).astype(np.float32)
    return x


def kick(dur=0.32):
    t = np.arange(int(dur * SR)) / SR
    f = 46 + 110 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    x[:96] += np.linspace(0.6, 0, 96) * np.sin(2 * np.pi * 1800 * t[:96])
    return np.tanh(x * 1.4).astype(np.float32)


def noise_hit(dur, f_lo, f_hi, decay, seed):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= ((f > f_lo) & (f < f_hi)).astype(float)
    x = np.fft.irfft(spec, n)
    x = x / (np.max(np.abs(x)) + 1e-9) * np.exp(-np.arange(n) / SR / decay)
    return x.astype(np.float32)


def pluck(f, dur=0.5, bright=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + bright * 0.5 * np.sin(2 * np.pi * 2 * f * t) + bright * 0.2 * np.sin(2 * np.pi * 3 * f * t)
    return (x * np.exp(-t / (dur * 0.28)) * np.minimum(1, t / 0.003)).astype(np.float32)


def add(buf, t, sig, gain=1.0, pan=0.0):
    s = int(round(t * SR))
    if s >= len(buf) or s < 0:
        return
    e = min(len(buf), s + len(sig))
    a = (pan + 1) * np.pi / 4
    buf[s:e, 0] += sig[:e - s] * gain * np.cos(a) * 1.4142
    buf[s:e, 1] += sig[:e - s] * gain * np.sin(a) * 1.4142


def lowpass(x, fc):
    """FFT ブリックウォール気味のローパス(なだらかな肩つき)。"""
    n = len(x)
    spec = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = 1 / (1 + (f / fc) ** 4)
    return np.fft.irfft(spec * (g[:, None] if x.ndim == 2 else g), n, axis=0).astype(np.float32)


def generate(plan):
    S, total, goal = plan['S'], plan['duration'], plan['GOAL_T']
    BAR = goal / 28.0
    BEAT = BAR / 4
    n = int(round(total * SR))
    nb = min(28, int(np.ceil(total / BAR)))        # 28 小節でちょうど終わる(29 小節目の頭は鳴らさない)
    q = lambda t: round(t / BEAT) * BEAT          # 拍に吸着
    t_orbit, t_gal, t_lap = q(S.get('orbit') or 13), q(S.get('galaxy') or 20), q(S.get('lap') or 30)
    t_zoom, t_never = q(S.get('zoom') or t_gal - 2), q(S.get('never') or 48)
    t_build = q(S.get('goal') or goal - 4 * BAR)   # 「見始めた場所は…」からゴールまでは溜め
    t_arp = q(S.get('who') or 3)
    # Dm → Bb → F → C の 4 小節循環(ルートは MIDI)。ゴールで D メジャーに解決。
    PROG = [(38, [62, 65, 69, 72]), (34, [58, 62, 65, 70]), (41, [60, 65, 69, 72]), (36, [60, 64, 67, 72])]
    drums = np.zeros((n, 2), np.float32); bass = np.zeros((n, 2), np.float32)
    pad = np.zeros((n, 2), np.float32); arp = np.zeros((n, 2), np.float32); pulse = np.zeros((n, 2), np.float32)
    K = kick(); HAT = noise_hit(0.05, 6000, 14000, 0.012, 1); OHAT = noise_hit(0.16, 5000, 13000, 0.05, 2)
    SN = noise_hit(0.2, 900, 7000, 0.06, 3) + 0.5 * pluck(190, 0.2, 0.2)[:int(0.2 * SR)]
    rng = np.random.default_rng(11)

    for b in range(nb):
        t0 = b * BAR
        root, chord = PROG[b % 4]
        final = t0 >= goal - 1e-6                  # ゴール後の最後の小節
        if final:
            root, chord = 38, [62, 66, 69, 74]     # D メジャー
        sec_gal = t_gal <= t0 < t_lap
        sec_lap = (t_lap <= t0 < t_build) or (t_zoom <= t0 < t_gal)   # ドラムを抜く区間
        sec_quiet = t_never <= t0 < t_build                          # いちばん静かな区間
        sec_build = t_build <= t0 < goal - 1e-6
        full = sec_gal or final
        # --- ドラム
        for k in range(4):
            tb = t0 + k * BEAT
            if not sec_lap and not final:
                if full or sec_build or k in (0, 2) or tb >= t_orbit:
                    add(drums, tb, K, 0.95 if full else 0.8)
            if final and k == 0:
                add(drums, tb, K, 1.0)
            if (full and k in (1, 3)) or (t_orbit <= t0 < t_gal and k == 3):
                add(drums, tb, SN, 0.42)
            if not sec_lap and not final:
                add(drums, tb + BEAT / 2, OHAT if (full and k == 3) else HAT, 0.26 if tb >= t_orbit else 0.17, 0.25)
                if full:
                    add(drums, tb + BEAT / 4, HAT, 0.12, -0.3); add(drums, tb + 3 * BEAT / 4, HAT, 0.12, 0.3)
        if sec_build:                              # スネアロール(だんだん細かく)
            p = (t0 - t_build) / max(BAR, goal - t_build)
            div = 4 if p < 0.25 else 8 if p < 0.5 else 16 if p < 0.75 else 32
            for j in range(div):
                tt = t0 + j * BAR / div
                add(drums, tt, SN, 0.10 + 0.34 * min(1.0, (tt - t_build) / max(BAR, goal - t_build)) ** 1.5)
        # --- ベース(8 分の刻み。キックの頭は避けて軽くうねらせる)
        if not final:
            for k in range(8):
                tb = t0 + k * BEAT / 2
                note = root if k % 4 != 3 else root + 12
                ln = int(BEAT / 2 * 0.86 * SR)
                x = (saw(midi(note), ln, harm=10 if not sec_lap else 4, bright=0.7) + 0.35 * saw(midi(note + 12), ln, harm=6, bright=0.6)) * env_adsr(ln, 0.004, 0.09, 0.55, 0.03)
                g = (0.5 if k % 2 == 0 else 0.62) * (0.55 if sec_lap else 1.0)
                add(bass, tb, x, g)
        else:
            ln = int(BAR * SR)
            add(bass, t0, saw(midi(root), ln, harm=5, bright=0.5) * env_adsr(ln, 0.005, 0.8, 0.5, 0.25), 0.6)
        # --- 中域の刻み(メーターが回り続ける感じ。スマホのスピーカーでも聞こえる帯域)
        if not final and not sec_lap:
            for k in range(8):
                tb = t0 + k * BEAT / 2
                m = (root + 24) if k % 2 == 0 else (root + 31)
                add(pulse, tb, pluck(midi(m), 0.16, 0.9), 0.30 if k % 4 == 0 else 0.2, -0.25 if k % 2 else 0.25)
        # --- パッド(冒頭は薄く、銀河の判明からフル。左右で少しずらして広げる)
        pad_g = 1.0 if t0 >= t_gal - 1e-6 else 0.42
        if True:
            ln = int((BAR + 0.5) * SR)
            env = env_adsr(ln, 0.25 if not final else 0.01, 0.6, 0.85, 0.5)
            for i, m in enumerate(chord):
                for ch, det in ((0, -0.006), (1, 0.006)):
                    x = saw(midi(m) * (1 + det), ln, harm=8, bright=0.5 if not sec_lap else 0.3, phase=rng.uniform(0, 6.28)) * env
                    s0 = int(round(t0 * SR)); e0 = min(n, s0 + ln)
                    pad[s0:e0, ch] += x[:e0 - s0] * (0.20 if i < 3 else 0.12) * (1.25 if final else pad_g)
        # --- アルペジオ(公転から。16 分。銀河 1 周の間は 8 分でまばらに高く)
        if t0 >= t_arp - 1e-6 and not final and not sec_quiet:
            early = t0 < t_orbit - 1e-6
            steps = 8 if (sec_lap or early) else 16
            pat = [0, 1, 2, 3, 2, 1, 2, 3, 0, 2, 1, 3, 2, 3, 1, 2]
            for k in range(steps):
                if sec_lap and rng.random() < 0.3:
                    continue
                tb = t0 + k * BAR / steps
                m = chord[pat[k % 16] % 4] + (24 if sec_lap else 12)
                g = (0.34 if full or sec_build else 0.15 if early else 0.24) * (0.8 + 0.2 * (k % 4 == 0))
                x = pluck(midi(m), 0.6 if sec_lap else 0.32, 0.5)
                pan = 0.6 if k % 2 == 0 else -0.6
                add(arp, tb, x, g, pan)
                add(arp, tb + BEAT * 0.75, x, g * 0.35, -pan)      # ピンポンディレイ
        if final:                                  # 解決の和音をきらめかせる
            for k, m in enumerate([74, 78, 81, 86, 81, 78, 74, 69]):
                add(arp, t0 + k * BAR / 8, pluck(midi(m), 0.7, 0.6), 0.4, 0.5 if k % 2 else -0.5)

    # キックに合わせてベースとパッドを少し引っ込める(サイドチェイン風)
    duck = np.ones(n, np.float32)
    for b in range(nb * 4):
        s = int(round(b * BEAT * SR))
        if s < n:
            ln = min(n - s, int(0.22 * SR))
            duck[s:s + ln] = np.minimum(duck[s:s + ln], 0.45 + 0.55 * np.linspace(0, 1, ln) ** 0.7)
    lap_mask = np.ones(n, np.float32)
    lap_mask[int(t_lap * SR):int(t_build * SR)] = 0   # ドラムのない区間はダッキングしない
    lap_mask[int(t_zoom * SR):int(t_gal * SR)] = 0
    duck = 1 - (1 - duck) * lap_mask
    bass = lowpass(bass, 1100) * duck[:, None]
    pad = lowpass(pad, 3200) * (0.6 + 0.4 * duck[:, None])
    mix = 0.62 * drums + 0.40 * bass + 1.25 * pad + 1.05 * lowpass(arp, 7000) + 1.2 * lowpass(pulse, 5000)
    # 45Hz 以下は切る(小さいスピーカーでは鳴らず、音量だけ食うため)
    spec = np.fft.rfft(mix, axis=0); f = np.fft.rfftfreq(n, 1 / SR)
    mix = np.fft.irfft(spec * (1 / np.sqrt(1 + (45 / np.maximum(f, 1)) ** 8))[:, None], n, axis=0).astype(np.float32)
    # 全体の抑揚: 冒頭は 85%、銀河で 100%、銀河 1 周で 80%、ゴールへ向けて 100%
    tt = np.arange(n) / SR
    dyn = np.interp(tt, [0, t_zoom, t_gal - 0.05, t_gal, t_lap, t_lap + 1, t_never, t_never + 0.5, t_build, t_build + 0.5, total],
                    [0.85, 0.85, 0.6, 1.0, 1.0, 0.8, 0.8, 0.55, 0.6, 0.9, 1.0]).astype(np.float32)
    mix *= dyn[:, None]
    mix[:int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))[:, None]
    mix[-int(0.006 * SR):] *= np.linspace(1, 0, int(0.006 * SR))[:, None]   # クリック防止の極短フェードのみ(曲はフェードアウトしない)
    mix = np.tanh(mix / (np.max(np.abs(mix)) + 1e-9) * 1.6) / np.tanh(1.6)
    return (mix * 0.9).astype(np.float32)


if __name__ == '__main__':
    plan = json.load(open(os.path.join(HERE, 'build', 'plan.json'), encoding='utf-8'))
    x = generate(plan)
    out = os.path.join(HERE, 'build', 'bgm.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print('wrote', out, f'{len(x) / SR:.2f}s')
