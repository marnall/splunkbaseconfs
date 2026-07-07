#!/usr/bin/env python

import os
import sys

app_dependencies_path = os.path.join(
    os.environ.get('SPLUNK_HOME'),
    'etc',
    'apps',
    'splunk_ta_onelogin',
    'lib'
)
if app_dependencies_path not in sys.path:
    sys.path.append(app_dependencies_path)

from api import Api

# Splunk sends session_key to the standard input when runs script
session_key = sys.stdin.readline().strip()
Api(session_key).fetch_user_count()
