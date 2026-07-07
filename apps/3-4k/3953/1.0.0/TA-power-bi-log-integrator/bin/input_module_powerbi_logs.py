
# encoding = utf-8

import os
import sys
import time
import datetime
import subprocess

def validate_input(helper, definition):
    connection_uri = definition.parameters.get('connection_uri', None)
    user_name = definition.parameters.get('user_name', None)
    password = definition.parameters.get('password', None)
    destination_folder = definition.parameters.get('destination_folder', None)
    log_search_start_date = definition.parameters.get('log_search_start_date', None)
    log_search_end_date = definition.parameters.get('log_search_end_date', None)
    result_size = definition.parameters.get('result_size', None)

def collect_events(helper, ew):
    opt_connection_uri = helper.get_arg('connection_uri')
    opt_user_name = helper.get_arg('user_name')
    opt_password = helper.get_arg('password')
    opt_destination_folder = helper.get_arg('destination_folder')
    opt_log_search_start_date = helper.get_arg('log_search_start_date')
    opt_log_search_end_date = helper.get_arg('log_search_end_date')
    opt_result_size = helper.get_arg('result_size')
    
    powerShellPath = r'C:\WINDOWS\system32\WindowsPowerShell\v1.0\powershell.exe'
    powerShellCmd = r'C:\Progra~1\Splunk\etc\apps\TA-power-bi-log-integrator\bin\scripts\input_module_powerbi_logs.ps1'

    p = subprocess.Popen([powerShellPath, '-ExecutionPolicy', 'RemoteSigned', powerShellCmd, opt_connection_uri, opt_user_name, opt_password, opt_destination_folder, opt_log_search_start_date, opt_log_search_end_date, opt_result_size], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()

    dt = str(datetime.date.today())
    data = dt + str(output)

    event = helper.new_event(data, host=None, source=None, sourcetype='ps_script', done=True, unbroken=True)

    try:
        ew.write_event(event)
    except Exception as e:
        raise e