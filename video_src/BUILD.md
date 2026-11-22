# 動画の作り方（痰のひみつ）

前提: VOICEVOX CORE 0.16（Python wheel）、voicevox_onnxruntime 1.17.3、0.vvm、open_jtalk_dic_utf_8-1.11 を /home/user/vv に置く。ffmpeg と Playwright が必要。

1. `python3 tts.py` … lines.json のセリフを四国めたん（style 2）で音声化し、読み（カナ）を表示
2. `python3 build_audio.py` … timeline.json・narration.wav・sfx.wav・bgm.wav を作成
3. `DSF=1.5 node render.js` … frames/ に 1920x1080 の連番 JPEG を書き出し（`ONLY=10,20` でプレビュー静止画）
4. ffmpeg で frames + narration + bgm（ナレーション中は自動で小さく）+ sfx を合成し、-14 LUFS に整える

セリフや字幕を変えるときは lines.json を編集する（`t` は読み上げ用、`sub` は字幕で【】が黄色の強調）。
要素が出るタイミングは appear.json に [セリフID, セリフ内の位置 0〜1] で書く。
