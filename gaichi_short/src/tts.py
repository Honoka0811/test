import json, urllib.request, urllib.parse, wave, sys, os
OUT = sys.argv[1]
lines = [
 ("hook", 81, "戦前、日本が治めた外地。いちばん人口が多かった都市は、どこだと思いますか？"),
 ("title",81, "外地の都市、人口ランキング、トップテン！"),
 ("r10", 13, "第10位。台湾、たかお。約16万人。"),
 ("r9",  13, "第9位。たいなん。約16万人。"),
 ("r8",  13, "第8位。朝鮮、じんせん。約17万人。"),
 ("r7",  13, "第7位。たいきゅう。約18万人。"),
 ("r6",  13, "第6位。北の港町、せいしん。約20万人。"),
 ("r5",  13, "第5位。ふざん。約25万人。住民の2割が内地人でした。"),
 ("r4",  13, "第4位。へいじょう。約29万人。"),
 ("r3",  81, "第3位！たいほく。約35万人。4人に1人が内地人！"),
 ("r2",  81, "第2位！関東州、だいれん。約55万人。住民の7割は中国人でした。"),
 ("tease",13, "そして、栄えある第1位は……"),
 ("r1",  81, "けいじょう！今のソウルです！約93万人。京都や神戸に迫る、大都市でした！"),
 ("extra",13, "ここからは、おまけ。"),
 ("kara",13, "樺太の中心、とよはらは約4万人。住民のほとんどが内地人でした。"),
 ("nanyo",13, "南洋群島では、パラオのコロールと、サイパンのガラパンが、1万人規模の町。沖縄出身の移民が多く暮らしました。"),
 ("hoppo",13, "そして北方領土。ここは外地ではなく北海道の一部。四島でおよそ1万7千人が、漁業を中心に暮らしていました。"),
 ("outro",81, "あなたの予想は当たりましたか？コメントで教えてください！"),
]
KANA = {
 "hook": "センゼン'、ニホ'ンガ/オサメ'タ/ガ'イチ、イチバン'/ジンコオガ'/オオ'カッタ/ト'シワ、ド'コダト/オモイマ'_スカ？",
 "r9": "ダ'イ/キュウイ'、タイナン'、ヤ'クジュウ/ロクマン'ニン",
 "r6": "ダ'イ/ロクイ'、_キタノ'/ミナトマチ'、セイシン'、ヤ'ク/ニ'ジュウ/マン'ニン",
 "r5": "ダ'イ/ゴイ'、フザン'、ヤ'ク/ニ'ジュウ/ゴマン'ニン、ジュウミンノ'/ニ'ワリガ/ナイチ'ジンデ_シタ",
 "kara": "カラ_フトノ'/チュウシン'、トヨハラワ'/ヤ'ク/ヨンマン'ニン、ジュウミンノ'/ホト'ンドガ/ナイチ'ジンデ_シタ",
}
meta=[]
for key, spk, text in lines:
    q = urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:50021/audio_query?speaker={spk}&text="+urllib.parse.quote(text), method="POST")).read()
    qj = json.loads(q)
    if key in KANA:
        ap = urllib.request.urlopen(urllib.request.Request(
            f"http://127.0.0.1:50021/accent_phrases?speaker={spk}&is_kana=true&text="+urllib.parse.quote(KANA[key]), method="POST")).read()
        qj["accent_phrases"] = json.loads(ap)
    qj["speedScale"]=1.28; qj["intonationScale"]=1.25; qj["prePhonemeLength"]=0.05; qj["postPhonemeLength"]=0.1
    if spk==81: qj["speedScale"]=1.2
    wav = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:50021/synthesis?speaker={spk}",
        data=json.dumps(qj).encode(), headers={"Content-Type":"application/json"})).read()
    p=os.path.join(OUT,key+".wav"); open(p,"wb").write(wav)
    with wave.open(p) as w: d=w.getnframes()/w.getframerate()
    meta.append({"key":key,"dur":round(d,3)}); print(key, round(d,2))
json.dump(meta, open(os.path.join(OUT,"meta.json"),"w"), ensure_ascii=False)
print("total", sum(m["dur"] for m in meta))
