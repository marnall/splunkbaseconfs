#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-21 18:48:26
# @ LastEditors: tukechao
# @ LastEditTime: 2023-02-13 16:07:01
# @ FilePath: /splunk-app/bin/cmd_qax_ti_tde_compromise.py
# @ description:

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))

from bin.qianxin_ti.model_tde import TdeHelper

if __name__ == "__main__":
    ins = TdeHelper()
    ins.main()
