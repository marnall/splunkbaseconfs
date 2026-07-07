
# encoding = utf-8

import os
import sys
import time
import datetime
import requests

def isCheckpoint(check_file, chkpntID):
    file_exists = os.path.isfile(check_file) 
    if file_exists:
        with open(check_file, 'r') as file:
            chkpntID_list = file.read().splitlines()
    else:
        with open(check_file, 'w+') as file:
            chkpntID_list = file.read().splitlines()

    return (chkpntID in chkpntID_list)

def write2Checkpoint(check_file, log):
    with open(check_file,'a') as file:
        file.writelines(log + '\n')

def write2Splunk(helper, ew, data, tStamp):
    event = helper.new_event(data, time=tStamp, host=None, done=True, unbroken=True)

    try:
        ew.write_event(event)
    except Exception as e:
        raise e

def validate_input(helper, definition):
    access_logs_endpoint = definition.parameters.get('access_logs_endpoint', None)
    token = definition.parameters.get('token', None)
    pages_to_retrieve = definition.parameters.get('pages_to_retrieve', None)

def collect_events(helper, ew):
    opt_access_logs_endpoint = helper.get_arg("access_logs_endpoint")
    opt_token = helper.get_arg("token")
    opt_pages_to_retrieve = helper.get_arg("pages_to_retrieve")

    pag = 0
    # Path para el archivo de checkpoint utilizado por eventos console
    dtFile = str(datetime.datetime.now().strftime("%Y%m%d"))
    check_file = os.path.join('/', os.path.dirname(os.path.abspath(__file__)), 'checkpoint', dtFile + '-slackAccesses.chk')

    while pag < int(opt_pages_to_retrieve):
        payload = {'token': opt_token}
        pag += 1
        response = requests.get(opt_access_logs_endpoint + '?count=1000&page=' + str(pag), params=payload).json()

        for l in range(len(response['logins'])):

            user_id = response['logins'][l]['user_id']
            username = response['logins'][l]['username']
            date_first = response['logins'][l]['date_first']
            date_last = response['logins'][l]['date_last']
            count = response['logins'][l]['count']
            ip = response['logins'][l]['ip']
            user_agent = response['logins'][l]['user_agent']
            user_agent = user_agent.replace(",", "")

            linea = str(user_id) + "," + str(username) + "," + str(date_first) + "," + str(date_last) + "," + str(count) + "," + str(ip) + "," + str(user_agent)

            # Si no existe en el archivo de checkpoint, entonces guardo el contenido de "checkline" en el archivo
            if not isCheckpoint(check_file, linea):
                tsLast = str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(date_last))))
                write2Splunk(helper, ew, linea, tsLast)

                write2Checkpoint(check_file, linea)