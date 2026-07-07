# encoding = utf-8

import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json
import subprocess


def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    pvx_api_key = ""
    try:
        cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
        with open(cwd, 'r') as file:
            pvx_api_key = file.read().splitlines()[0]
    except:
        return None

    _NEW_PYTHON_PATH = '/usr/bin/python3'
    _SPLUNK_PYTHON_PATH = os.environ['PYTHONPATH']

    os.environ['PYTHONPATH'] = _NEW_PYTHON_PATH
    my_process = os.path.join(os.getcwd(), os.path.dirname(os.path.abspath(__file__))+'/real_time_predict.py')
    
    p = subprocess.Popen(['/usr/bin/python3', my_process, _SPLUNK_PYTHON_PATH,helper.get_global_setting("ip_address"),pvx_api_key,helper.get_global_setting('time_offset')],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.communicate()[0]
    
    
    if output.strip() != '':
        output = json.loads(output)
    else:
        output = {'isalert': 'False', 'pakets_count': 0}
    
    data = {
        'action' : 'allowed',
        'app' : 'Accedian_ML',
        'data' : output 
        }
    event = helper.new_event(source=helper.get_input_type(),index=helper.get_output_index(),sourcetype=helper.get_sourcetype(),data=json.dumps(data),done=True,unbroken=True)
    
    ew.write_event(event)
