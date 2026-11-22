import glob,json,wave,dataclasses
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
so=glob.glob('/home/user/vv/voicevox_onnxruntime*/lib/libvoicevox_onnxruntime.so')[0]
s=Synthesizer(Onnxruntime.load_once(filename=so), OpenJtalk('/home/user/vv/open_jtalk_dic_utf_8-1.11'))
with VoiceModelFile.open('/home/user/vv/0.vvm') as m: s.load_voice_model(m)
L=json.load(open('lines.json'))
mt=lambda ap:''.join(m.text for m in ap.moras)
for i,l in enumerate(L):
    q=s.create_audio_query(l['t'],2)
    aps=list(q.accent_phrases)
    for j in range(len(aps)-1):
        if mt(aps[j])=='シコクメ':
            name=list(s.create_accent_phrases_from_kana("シ'コク/メ'タン",2))
            name[-1]=dataclasses.replace(name[-1],pause_mora=aps[j+1].pause_mora)
            # keep particle after タン (e.g. タンガ)
            rest=mt(aps[j+1])[2:]
            if rest:
                name=list(s.create_accent_phrases_from_kana("シ'コク/メ'タン"+rest,2)); name[-1]=dataclasses.replace(name[-1],pause_mora=aps[j+1].pause_mora)
            aps[j:j+2]=name; aps=s.replace_mora_data(aps,2); break
    q.accent_phrases=aps
    q.speed_scale=1.15; q.pre_phoneme_length=0.05; q.post_phoneme_length=0.05; q.intonation_scale=1.15
    open(f'voice/{i:02d}.wav','wb').write(s.synthesis(q,2))
    w=wave.open(f'voice/{i:02d}.wav'); l['dur']=w.getnframes()/w.getframerate()
    print(l['id'],round(l['dur'],2),'/'.join(mt(a) for a in aps))
json.dump(L,open('lines_d.json','w'),ensure_ascii=False)
