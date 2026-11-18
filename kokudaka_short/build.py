"""石高ショート動画シリーズのビルド入口
使い方: VOICEVOXエンジンを localhost:50021 で起動してから
  python3 build.py          # 全話
  python3 build.py ep2      # 指定した話だけ
"""
import importlib, sys
from core import render

if __name__ == "__main__":
    for name in sys.argv[1:] or ["ep1", "ep2", "ep3"]:
        print(f"==== {name} ====")
        render(importlib.import_module(name))
