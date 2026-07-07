#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Author :Imocence
@Date   :2024/4/9
@Notes  :
"""
import os
import sys

localDir = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'tjym', 'bin')
if localDir not in sys.path:
    sys.path.append(localDir)
