#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-21 18:48:26
# @ LastEditors: tukechao
# @ LastEditTime: 2023-07-13 15:48:38
# @ FilePath: /splunk-app/bin/cmd_qax_home_page_statistic.py
# @ description:

import os
import sys
import traceback
import configparser
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))
from bin.qianxin_ti.common_log import logger
from bin.qianxin_ti.common_util import QianxinConfHelper
from bin.qianxin_ti.common_request_util import requests_api
from bin.qianxin_ti.common_constants import (
    TIP_HOME_STATISTIC_FILE_NAME,
    TIP_HOME_STATISTIC_FILE_PATH,
    QAX_CONF_DEBUG_PATH,
)


class TipHomePageStatisticHelper:
    def __init__(self):
        pass

    def fetch_data_from_tip(self) -> bool:
        try:
            tip_info = QianxinConfHelper.verify_current_tip_token()
            if tip_info:
                url = "/api/v2/thirdparty-dashboard/home-page-statistics"
                headers = {"Api-Key": tip_info[1]}
                res = requests_api.query_common(
                    tip_info[0] + url, method="get", stream=True, headers=headers, verify=False
                )
                with open(os.path.join(TIP_HOME_STATISTIC_FILE_PATH, TIP_HOME_STATISTIC_FILE_NAME), "wb") as fd:
                    for chunk in res.iter_content(chunk_size=1024 * 1000):
                        if chunk:
                            fd.write(chunk)
                            fd.flush()
                return True
            else:
                logger.error("Invalid tip host/token.")
                logger.error(f"Bad Connection info:{tip_info}")
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def run(self) -> None:
        flag = self.fetch_data_from_tip()
        if flag:
            logger.info("Tip home page statistics info SUCCESSFULLY updated.")
        else:
            logger.warning("FAILED to update tip home page statistics.")
            time.sleep(15)
            self.fetch_data_from_tip()


if __name__ == "__main__":
    ins = TipHomePageStatisticHelper()
    ins.run()
