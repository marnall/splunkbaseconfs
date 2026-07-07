#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project:
@File   :rest_api_job.py
@Author :Imocence
@Date   :2024/3/20 
"""
import json
import os
import sys

localDir = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'tjym', 'bin')
if localDir not in sys.path:
    sys.path.append(localDir)
from splunk.persistconn.application import PersistentServerConnectionApplication
from tj_business import Business


class RestApiJob(PersistentServerConnectionApplication):

    def __init__(self, _command_line, _command_arg):
        self.apiService = Business()
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        result, result_status = self.apiService.apiJob(in_string)
        return {
            'payload': json.dumps(result),
            'status': result_status,
            'headers': {
                'Content-Type': 'application/json'
            },
        }

    def handleStream(self, handle, in_string):
        """
        以供将来使用
        """

        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        可以选择重写的虚方法，以便在请求完成后接收回调。
        """
        pass
