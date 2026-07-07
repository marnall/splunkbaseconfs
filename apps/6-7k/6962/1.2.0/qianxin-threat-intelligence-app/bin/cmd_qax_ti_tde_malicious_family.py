#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-21 18:48:26
# @ LastEditors: tukechao
# @ LastEditTime: 2023-06-20 17:11:19
# @ FilePath: /splunk-app/bin/cmd_qax_ti_tde_malicious_family.py
# @ description:

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))

from bin.qianxin_ti.model_log_detection import LogDetectionMaliciousFamilyInfoModel
from bin.qianxin_ti.common_util import ApiHelper

if __name__ == "__main__":
    """
    In this command, we will update the malicious_family info with latest online data.
    If it's not cloud version, it won't work.
    """
    _api = ApiHelper("", mock=True)
    ins = LogDetectionMaliciousFamilyInfoModel(_api)
    ins.update_malicious_family_info_info()
