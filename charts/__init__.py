# -*- coding: utf-8 -*-
"""图型实现包。

这里的模块**不做 sys.path 手脚**。`import tokens` 能成立，靠的是所有入口
（demo.py / demo_palettes.py / tests/run.py / scripts/validate.py）
都已经把仓库根目录放进 sys.path。每个图型各插一遍是 15 份一模一样的噪音，
而且会让「这个模块能不能单独跑」显得像是有人认真考虑过——并没有，
charts/ 下没有任何模块带 __main__。
"""
