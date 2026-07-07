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
from config import Config

timestamp = Config('onelogin_events').get('events', 'last_event_timestamp')

if timestamp:
    time1 = timestamp.split('+')
    time2 = time1[0].split(' ')
    timestamp = time2[0] + 'T' + time2[1] + 'Z'
else:
    timestamp = Config('onelogin').get('onelogin_api', 'start_userdate')

params = {'since': timestamp}

# Splunk sends session_key to the standard input when runs script
session_key = sys.stdin.readline().strip()
Api(session_key).fetch_all_events(params)
