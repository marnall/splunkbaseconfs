#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project:
@File   :rest_index.py
@Author :Imocence
@Date   :2023/10/24 
"""
import json
import os
import sys

localDir = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'tjym', 'bin')
if localDir not in sys.path:
    sys.path.append(localDir)
from splunk.persistconn.application import PersistentServerConnectionApplication
from tj_business import Business


class RestIndex(PersistentServerConnectionApplication):
    '''
    https://127.0.0.1:8089/servicesNS/-/tjym/rest-index
    '''

    def __init__(self, _command_line, _command_arg):
        self.apiService = Business()
        super(PersistentServerConnectionApplication, self).__init__()

    # 处理一个来自splunkd的同步。
    def handle(self, in_string):
        """
        为简单的同步请求调用。
        @param in_string: 传入的请求数据
        @rtype: 字符串或字典
        @return: 响应返回的字符串。 如果传入了一个字典，它将在返回之前自动进行JSON编码。
        """
        return {
            'payload': json.dumps({'page': str(self.apiService.index()), 'path': str(os.path.dirname(os.path.abspath(__file__)))}),
            'status': 200,
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
