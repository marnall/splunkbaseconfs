#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2023-01-11 16:49:55
# @ LastEditors: tukechao
# @ LastEditTime: 2023-06-20 10:10:12
# @ FilePath: /splunk-app/bin/cmd_qax_ti_log_detection_statistics.py
# @ description:

import os
import sys
import traceback
import json
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")),
)
from typing import List, Dict, Tuple, Any, NoReturn
from bin.qianxin_ti.common_log import logger
from bin.qianxin_ti.common_util import QianxinConfHelper, ApiHelper
from bin.qianxin_ti.model_log_detection_statistics import LogDetectionStatisticModel


class TipLogDetectionStatisticsBackgroundWorker:
    """Generate Statistic information each several hours"""

    def run(self) -> None:
        lds = LogDetectionStatisticModel(api=ApiHelper(None, mock=True))
        # lds.run()
        lds.update_data()
        logger.debug("Run Log Detection statistic")


if __name__ == "__main__":
    ins = TipLogDetectionStatisticsBackgroundWorker()
    ins.run()
