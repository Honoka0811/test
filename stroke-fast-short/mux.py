# -*- coding: utf-8 -*-
"""無音の映像(capture.js の出力)に mix.wav を合成して output/stroke_fast.mp4 を作る。使い方: python3 mux.py"""
import os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'output')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'stroke_fast_silent.mp4'), '-i', os.path.join(OUT, 'mix.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', os.path.join(OUT, 'stroke_fast.mp4')], check=True)
print('wrote output/stroke_fast.mp4')
