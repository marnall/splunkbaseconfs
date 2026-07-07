#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-23 14:22:58
# @ LastEditors: tukechao
# @ LastEditTime: 2022-11-29 01:56:43
# @ FilePath: /splunk-app/bin/cmd_restart.py
# @ description:quick restart command

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))
from bin.qianxin_ti.common_log import logger
from bin.qianxin_ti.common_util import QianxinConfHelper

logger.info("Splunk restart command")

service = QianxinConfHelper.get_splunk_service()
service.restart()
