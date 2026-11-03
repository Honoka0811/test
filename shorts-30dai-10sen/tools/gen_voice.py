import json, sys, re, wave
from voicevox_core import VoicevoxCore
S = sys.argv[1]; D = sys.argv[2]
core = VoicevoxCore(open_jtalk_dict_dir=f'{D}/vv/ojt/open_jtalk_dic_utf_8-1.11')
SID = 2  # 四国めたん ノーマル
core.load_model(SID)
SPEED = 1.2
lines = [
 ("intro", "さんじゅう代のうちに、やっておくべきこと、じゅっせん！サクッと紹介するよ。"),
 ("01", "そのいち、健康に投資する。運動習慣と人間ドック。さんじゅう代で始めた人が、あとで差をつけるよ。"),
 ("02", "そのに、お金を仕組み化する。先取り貯金と、積み立て投資で、ほったらかしで増やそう。"),
 ("03", "そのさん、自分の武器をひとつ磨く。これが得意、と言い切れる専門性を作ろう。"),
 ("04", "そのよん、人間関係を整える。一緒にいて元気になれる人と、時間を過ごそう。"),
 ("05", "そのご、親と旅行に行く。一緒に過ごせる時間は、思っているより、ずっと短いんだ。"),
 ("06", "そのろく、一度は大きく挑戦する。転職でも起業でも、さんじゅう代は、まだやり直せる。"),
 ("07", "そのなな、住む場所と環境を整える。毎日の快適さが、人生の質を決めるよ。"),
 ("08", "そのはち、学び直しをする。本でも資格でも、さんじゅう代の勉強は、いちばんコスパがいい。"),
 ("09", "そのきゅう、一生モノの趣味を見つける。仕事以外の居場所が、心を守ってくれる。"),
 ("10", "そのじゅう、写真と日記で、今を記録に残す。今の自分は、今しかいないから。"),
 ("outro", "全部やらなくてオッケー。ひとつ選んで、今日から始めよう！"),
]
DISP = [("さんじゅう代","30代"),("じゅっせん","10選"),("そのいち","その1"),("そのに","その2"),("そのさん","その3"),("そのよん","その4"),
        ("そのご","その5"),("そのろく","その6"),("そのなな","その7"),("そのはち","その8"),("そのきゅう","その9"),("そのじゅう","その10"),("オッケー","OK")]
out = []
for key, text in lines:
    q = core.audio_query(text, SID)
    q.speed_scale = SPEED; q.intonation_scale = 1.15; q.pitch_scale = 0.0; q.volume_scale = 1.0
    q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.08; q.output_sampling_rate = 48000
    # timing of pauses (punctuation boundaries)
    t = q.pre_phoneme_length / SPEED; pauses = []; starts = [t]
    for ap in q.accent_phrases:
        for m in ap.moras:
            t += ((m.consonant_length or 0) + m.vowel_length) / SPEED
        if ap.pause_mora is not None:
            pauses.append(round(t, 3)); t += ap.pause_mora.vowel_length / SPEED; starts.append(round(t, 3))
    wav = core.synthesis(q, SID)
    p = f'{S}/voice/{key}.wav'; open(p, 'wb').write(wav)
    with wave.open(p) as w: dur = w.getnframes() / w.getframerate()
    disp = text
    for a, b in DISP: disp = disp.replace(a, b)
    chunks = [c for c in re.split(r'(?<=[、。！])', disp) if c]
    # assign times: chunk i spans starts[i] .. pauses[i] (last chunk ends at dur)
    timed = []
    for i, c in enumerate(chunks):
        st = starts[i] if i < len(starts) else (timed[-1]['end'] if timed else 0)
        en = pauses[i] if i < len(pauses) else dur
        timed.append({"text": c, "start": round(st, 3), "end": round(en, 3)})
    ok = (len(pauses) in (len(chunks), len(chunks)-1))
    out.append({"key": key, "text": text, "disp": disp, "wav": p, "dur": round(dur, 3), "chunks": timed, "pause_ok": ok})
    print(key, round(dur, 2), 'pauses', len(pauses), 'chunks', len(chunks), [ (c['text'], c['start'], c['end']) for c in timed])
json.dump(out, open(f'{S}/voice/lines.json', 'w'), ensure_ascii=False, indent=1)
print("total", round(sum(o['dur'] for o in out), 2))
