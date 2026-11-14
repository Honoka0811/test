# -*- coding: utf-8 -*-
"""script.json → ナレーション音声(output/narration.wav)+ タイムライン(build/timeline.json)。

ナレーションを先に合成し、その実測タイミング(モーラ単位)から字幕チャンクと
映像キューの時刻を決める「音声先行」方式。映像側は timeline.json だけを見て描画する。

使い方: python3 tts.py [script.json] [--check]
  --check  音声を書き出さず、各行の読み(カナ)と長さだけ表示する(読み間違いの検品用)

環境変数:
  VOICEVOX_HOME  既定 /home/user/vv(ort/ vvms/ open_jtalk_dic_utf_8-1.11/ を置いた場所)
"""
import glob, io, json, os, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VV = os.environ.get('VOICEVOX_HOME', '/home/user/vv')
SR = 48000
FRAME = 256 / 24000.0  # VOICEVOX の 1 フレーム(秒)


def load_engine():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    ort_glob = glob.glob(os.path.join(VV, 'ort', '*', 'lib', 'libvoicevox_onnxruntime.so*'))
    ort = Onnxruntime.load_once(filename=os.environ.get('VOICEVOX_ORT', sorted(ort_glob)[0]))
    ojt = OpenJtalk(os.environ.get('VOICEVOX_DICT', os.path.join(VV, 'open_jtalk_dic_utf_8-1.11')))
    synth = Synthesizer(ort, ojt)
    for f in sorted(glob.glob(os.path.join(os.environ.get('VOICEVOX_VVMS', os.path.join(VV, 'vvms')), '*.vvm'))):
        with VoiceModelFile.open(f) as m:
            synth.load_voice_model(m)
    return synth, ojt


def style_name(synth, style):
    for c in synth.metas():
        for st in c.styles:
            if st.id == style:
                return f'{c.name}({st.name})'
    return str(style)


def n_moras(aps):
    return sum(len(ap.moras) for ap in aps)


def _pause_len(pm):
    """pause_mora は版によって dict / Mora のどちらでも返る。"""
    return pm['vowel_length'] if isinstance(pm, dict) else pm.vowel_length


def _scale_pause(pm, k):
    if isinstance(pm, dict):
        pm['vowel_length'] *= k
    else:
        pm.vowel_length *= k


def mora_table(q):
    """クエリ内の全モーラ(ポーズ含む)の (text, start, end, is_pause) を出力速度の秒で返す。"""
    sp = q.speed_scale
    fr = lambda sec: max(0, int(round(sec / sp / FRAME)))
    t = fr(q.pre_phoneme_length)
    rows = []
    for ap in q.accent_phrases:
        for m in ap.moras:
            n = (fr(m.consonant_length) if m.consonant_length else 0) + fr(m.vowel_length)
            rows.append((m.text, t * FRAME, (t + n) * FRAME, False))
            t += n
        if ap.pause_mora is not None:
            n = fr(_pause_len(ap.pause_mora))
            rows.append(('、', t * FRAME, (t + n) * FRAME, True))
            t += n
    total = (t + fr(q.post_phoneme_length)) * FRAME
    return rows, total


def resample(x, sr):
    if sr == SR:
        return x
    n = int(round(len(x) * SR / sr))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def synth_line(synth, ojt, line, voice):
    style = int(line.get('style', voice['style']))
    chunks = line['chunks']
    says = [c.get('say', c['show']) for c in chunks]
    text = ''.join(says)
    # "kana" があればアクセントつきの読みをそのまま使う(辞書のアクセントが不自然な行だけ指定する)
    q = synth.create_audio_query_from_kana(line['kana'], style) if 'kana' in line else synth.create_audio_query(text, style)
    q.speed_scale = float(line.get('speed', voice.get('speed', 1.0)))
    q.pitch_scale = float(line.get('pitch', voice.get('pitch', 0.0)))
    q.intonation_scale = float(line.get('intonation', voice.get('intonation', 1.0)))
    q.volume_scale = float(line.get('volume', voice.get('volume', 1.0)))
    q.pre_phoneme_length = 0.03
    q.post_phoneme_length = 0.06
    # 行内ポーズの長さ調整(読点の間が長すぎるとテンポが落ちる)
    ps = float(line.get('pause_scale', voice.get('pause_scale', 1.0)))
    if ps != 1.0:
        for ap in q.accent_phrases:
            if ap.pause_mora is not None:
                _scale_pause(ap.pause_mora, ps)
    rows, total = mora_table(q)
    voiced = [r for r in rows if not r[3]]
    # チャンク境界 = 「先頭からそのチャンクまで」を解析したときのモーラ数
    bounds, ok = [], True
    for k in range(len(chunks)):
        cnt = n_moras(ojt.analyze(''.join(says[:k + 1])))
        bounds.append(cnt)
    if bounds[-1] != len(voiced):
        ok = False
    if not ok or any(b > len(voiced) for b in bounds) or any(b2 <= b1 for b1, b2 in zip(bounds, bounds[1:])):
        # 読みが文脈で変わった場合は文字数比で按分する
        acc, tot = 0, sum(len(s) for s in says)
        bounds = []
        for s in says:
            acc += len(s)
            bounds.append(max(1, round(len(voiced) * acc / tot)))
        bounds[-1] = len(voiced)
        ok = False
    out_chunks, prev = [], 0
    for c, b in zip(chunks, bounds):
        seg = voiced[prev:b] or voiced[max(0, b - 1):b]
        oc = {k: v for k, v in c.items() if k != 'say'}
        oc['t0'] = round(seg[0][1], 4)
        oc['t1'] = round(seg[-1][2], 4)
        out_chunks.append(oc)
        prev = b
    return q, style, out_chunks, total, ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    check = '--check' in sys.argv
    path = args[0] if args else os.path.join(HERE, 'script.json')
    with open(path, encoding='utf-8') as f:
        script = json.load(f)
    voice = script['voice']
    synth, ojt = load_engine()
    print('voice:', style_name(synth, int(voice['style'])), voice)

    t = float(script.get('lead_in', 0.0))
    lines, cues, pieces = [], {}, []
    for line in script['lines']:
        q, style, chunks, total, ok = synth_line(synth, ojt, line, voice)
        t += float(line.get('gap_before', voice.get('gap', 0.12)))
        if 'at' in line:                       # 絶対時刻で置く行(例: ゴールの瞬間 56.13 秒)
            if float(line['at']) < t - 1e-6:
                print(f"  [!] {line['id']}: at={line['at']} より前の行が {t - float(line['at']):.2f}s はみ出しています")
            t = max(t, float(line['at']))
        start = t
        for c in chunks:
            c['t0'] = round(start + c['t0'], 3)
            c['t1'] = round(start + c['t1'], 3)
            if 'cue' in c:
                cues[c['cue']] = c['t0']
            if 'cue_end' in c:
                cues[c['cue_end']] = c['t1']
        entry = {'id': line['id'], 'start': round(start, 3), 'end': round(start + total, 3),
                 'kana': q.kana, 'chunks': chunks}
        for k in ('scene', 'style'):
            if k in line:
                entry[k] = line[k]
        lines.append(entry)
        cues[line['id']] = round(start, 3)
        cues[line['id'] + ':end'] = round(start + total, 3)
        flag = '' if ok else '  [!] チャンク境界は文字数按分'
        print(f"{start:6.2f}-{start + total:6.2f} ({total:4.2f}s) {line['id']:<10} {q.kana}{flag}")
        if not check:
            wav = synth.synthesis(q, style)
            with wave.open(io.BytesIO(wav)) as w:
                sr = w.getframerate()
                x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            pieces.append((start, resample(x, sr)))
        t = start + total
    duration = round(t + float(script.get('tail', 0.6)), 3)
    if 'duration' in script:                   # 尺を固定する(例: 56.15 秒 = メーターが地球の直径に届くフレームまで)
        if t > float(script['duration']) - 0.03:
            print(f"  [!] ナレーションが尺 {script['duration']}s を超えています(終わり {t:.2f}s)。speed か gap を詰めてください")
        duration = float(script['duration'])
    print(f'total duration: {duration:.2f}s')
    if check:
        return
    track = np.zeros(int(round(duration * SR)) + SR, dtype=np.float32)
    for start, x in pieces:
        f = min(240, len(x) // 4)
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
        s = int(round(start * SR))
        track[s:s + len(x)] += x
    track = track[:int(round(duration * SR))]
    track = track / (np.max(np.abs(track)) or 1) * 0.89
    os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
    wav_path = os.path.join(HERE, 'build', 'narration.wav')
    with wave.open(wav_path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    tl = {'duration': duration, 'fps': int(script.get('fps', 60)), 'lines': lines, 'cues': cues}
    with open(os.path.join(HERE, 'build', 'timeline.json'), 'w', encoding='utf-8') as f:
        json.dump(tl, f, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, 'build', 'timeline.js'), 'w', encoding='utf-8') as f:
        f.write('window.TIMELINE = ' + json.dumps(tl, ensure_ascii=False) + ';\n')
    print('wrote', wav_path, 'and build/timeline.{json,js}')


if __name__ == '__main__':
    main()
