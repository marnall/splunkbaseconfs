#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-21 18:48:26
# @ LastEditors: tukechao
# @ LastEditTime: 2023-01-30 18:35:56
# @ FilePath: /splunk-app/bin/cmd_qax_ti_log_detection.py
# @ description:

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))

from bin.qianxin_ti.model_log_detection_background_worker import TipLogDetectionBackgroundWorker

if __name__ == "__main__":
    ins = TipLogDetectionBackgroundWorker()
    ins.main()
