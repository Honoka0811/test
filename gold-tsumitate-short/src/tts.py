import json,urllib.request,urllib.parse,sys,wave
W=sys.argv[1]
L=[
 ("s1",81,"毎月たった五千円。三十年、金を積み立てたら、今いくらになったと思う？"),
 ("s2",13,"一九九六年から毎月五千円。払ったお金は、合計百八十万円。"),
 ("s3",13,"当時の金は、一グラムたったの千四百円。"),
 ("s4",81,"それが今や、約二万二千円！十五倍以上に爆上がり！"),
 ("s5",13,"コツコツ積み上がった金は、約六百七十五グラム。"),
 ("s6",13,"しかも、その半分以上は、金が安かった最初の十年で買えていたんです。"),
 ("s7",81,"気になる評価額は…"),
 ("s8",81,"なんと、約千四百八十万円！元本の、約八倍！"),
 ("s9",13,"安い時にたくさん買える。これが、積立の力。"),
 ("s10",81,"あなたなら、何を積み立てる？コメントで教えて！"),
]
out=[]
for k,sp,t in L:
  q=json.load(urllib.request.urlopen(urllib.request.Request(f"http://localhost:50021/audio_query?speaker={sp}&text="+urllib.parse.quote(t),method="POST")))
  q["speedScale"]=1.18; q["prePhonemeLength"]=0.05; q["postPhonemeLength"]=0.12
  if sp==81: q["intonationScale"]=1.25
  if k=="s7": q["speedScale"]=1.0
  wav=urllib.request.urlopen(urllib.request.Request(f"http://localhost:50021/synthesis?speaker={sp}",data=json.dumps(q).encode(),headers={"Content-Type":"application/json"})).read()
  open(f"{W}/voice/{k}.wav","wb").write(wav)
  with wave.open(f"{W}/voice/{k}.wav") as w: d=w.getnframes()/w.getframerate(); sr=w.getframerate()
  out.append((k,t,round(d,3))); print(k,round(d,2),sr)
json.dump(out,open(f"{W}/voice/lines.json","w"),ensure_ascii=False)
