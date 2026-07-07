#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-16 19:11:17
# @ LastEditors: tukechao
# @ LastEditTime: 2023-01-11 14:22:36
# @ FilePath: /splunk-app/bin/cmd_qax_mock_data.py
# @ description: mock data to splunk for test perpose

import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import qianxin_threat_intelligence_app_declare  # noqa: F401
import sys


from splunklib.searchcommands import dispatch, EventingCommand, Configuration


@Configuration()
class ExEventsCommand(EventingCommand):
    def transform(self, records):
        l = list(records)
        l.sort(key=lambda r: r["_raw"])
        return l


if __name__ == "__main__":
    dispatch(ExEventsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
