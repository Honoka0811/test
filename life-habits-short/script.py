# -*- coding: utf-8 -*-
"""動画の台本(唯一の正本)。narrate.py がこれを読み上げ、実際の発話長から timeline.js を作る。
read  … VOICEVOX に渡す読み上げ文(読み間違いを防ぐため数字はかな/漢数字)
text  … 画面・字幕に出す表記
hl    … 画面で黄色マーカーを引くキーワード(text に含まれる文字列)
"""

TITLE = '人生を楽しくする習慣10選'

HOOK = [
    dict(read='毎日、なんとなく、つまらない…?', text='毎日なんとなく\nつまらない…', hl='つまらない'),
    dict(read='人生を楽しくする習慣、十選!', text='人生を楽しくする\n習慣10選!', hl='習慣10選'),
    dict(read='第一位は、最後に発表するよ!', text='1位は最後に発表!', hl='1位'),
]

# 10位 → 2位 の順(1位は別扱い)
HABITS = [
    dict(rank=10, emoji='☀️', title='朝日を浴びる', theme='sunrise',
         read_title='第十位、朝日を浴びる!',
         read='体内時計が整って、朝からスッキリ!',
         text='体内時計が整って\n朝からスッキリ!', hl='体内時計'),
    dict(rank=9, emoji='🚶', title='1日10分歩く', theme='mint',
         read_title='第九位、一日じゅっぷん歩く!',
         read='気分がすっきりして、アイデアも湧いてきます。',
         text='気分すっきり\nアイデアも湧いてくる!', hl='アイデア'),
    dict(rank=8, emoji='📵', title='寝る前はスマホを置く', theme='night',
         read_title='第八位、寝る前はスマホを置く!',
         read='睡眠の質が上がって、目覚めが変わります。',
         text='睡眠の質が上がって\n目覚めが変わる!', hl='睡眠の質'),
    dict(rank=7, emoji='🙏', title='「ありがとう」を口に出す', theme='peach',
         read_title='第七位、ありがとうを口に出す!',
         read='相手も自分も、明るい気持ちになれます。',
         text='相手も自分も\n明るい気持ちに!', hl='相手も自分も'),
    dict(rank=6, emoji='📝', title='よかったことを3つ書く', theme='lemon',
         read_title='第六位、よかったことを三つ書く!',
         read='小さな幸せに、気づけるようになります。',
         text='寝る前に3つ書くだけで\n小さな幸せに気づける', hl='小さな幸せ'),
    dict(rank=5, emoji='🚀', title='月1回「初めて」に挑戦', theme='sky',
         read_title='第五位、月に一回、初めてに挑戦!',
         read='初めての体験が、毎日を新鮮にしてくれます。',
         text='初めての体験で\n毎日が新鮮に!', hl='新鮮'),
    dict(rank=4, emoji='🎁', title='自分にご褒美を用意する', theme='berry',
         read_title='第四位、自分にご褒美を用意する!',
         read='小さなご褒美で、毎日にメリハリが生まれます。',
         text='小さなご褒美で\n毎日にメリハリ!', hl='メリハリ'),
    dict(rank=3, emoji='🧹', title='5分だけ片付ける', theme='aqua',
         read_title='第三位、五分だけ片付ける!',
         read='部屋が整うと、心も整います。',
         text='部屋が整うと\n心も整う!', hl='心も整う'),
    dict(rank=2, emoji='🤝', title='誰かに小さな親切をする', theme='coral',
         read_title='第二位、誰かに小さな親切をする!',
         read='人のための行動は、自分の幸せ度も上げてくれます。',
         text='人のための行動で\n自分の幸せ度もアップ!', hl='幸せ度'),
]

TEASER = dict(read='そして、第一位は…', text='そして第1位は…', hl='第1位')

FIRST = dict(rank=1, emoji='📅', title='楽しみな予定を先に入れる', theme='gold',
             read_title='第一位!楽しみな予定を、先に入れる!',
             read='待っている時間も、ずっとワクワクできるんです。',
             text='待っている時間も\nずっとワクワク!', hl='ワクワク')

OUTRO = [
    dict(read='気になった習慣は何番?コメントで教えてね!', text='試したいのは何番?\nコメントで教えてね', hl='何番'),
]
