#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-21 18:48:26
# @ LastEditors: tukechao
# @ LastEditTime: 2023-04-06 10:35:54
# @ FilePath: /splunk-app/bin/cmd_qax_ti_log_detection_all.py
# @ description:

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))

from bin.qianxin_ti.model_log_detection_background_worker import TipLogDetectionBackgroundWorker

if __name__ == "__main__":
    ins = TipLogDetectionBackgroundWorker()
    ins.main(all=True)
