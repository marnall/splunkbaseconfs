#!/usr/bin/env python3
# Written by mohlcyber v.1.0.0 (24.11.2021)
# Script to pull MVISION UCE Logs

import os
import sys
import requests
import logging.handlers
import time
import json
import re

from xml.etree import ElementTree
from datetime import datetime, timedelta

logger = logging.getLogger('mvuce_logs')
logger.propagate = False
logger.setLevel(logging.DEBUG)
file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/mvuce_logs.log',
                                                    maxBytes=25000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class UCE():
    def __init__(self, creds, proxy, exec_time):
        self.base_url = 'https://msg.mcafeesaas.com:443/mwg/api'
        self.cid = creds[0]['cid']

        user = creds[0]['user']
        pw = creds[0]['pwd']

        self.session = requests.Session()
        self.session.headers = {
            'Accept': 'text/xml',
            'x-mwg-api-version': '5'
        }
        self.session.auth = (user, pw)

        if len(proxy) > 0:
            session_proxy = '{0}://{1}@{2}:{3}'.format(proxy[0]['proxy'][0], proxy[0]['userpwd'], proxy[0]['proxy'][1],
                                                       proxy[0]['proxy'][2])
            self.session.proxies['https'] = session_proxy

        if exec_time is None:
            new_pull = (datetime.now() - timedelta(minutes=60)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            self.epoch_from = int(time.mktime(time.strptime(new_pull, '%Y-%m-%dT%H:%M:%S.%fZ')))
        else:
            self.epoch_from = exec_time

    def get_logs(self):
        params = {
            'filter.requestTimestampFrom': self.epoch_from,
            'order.0.requestTimestamp': 'desc'
        }

        res = self.session.get('{0}/reporting/forensic/{1}'.format(self.base_url, self.cid), params=params)

        if res.ok:
            exec_time = None
            res_obj = []
            xml = ElementTree.fromstring(res.text)
            for elem in xml:
                res_obj.append(elem.attrib)

            if len(res_obj) > 0:
                exec_time = int(res_obj[0]['request_timestamp_epoch']) + 1

            return exec_time, res_obj

        else:
            logger.error('Error in uce.get_logs. {0} - {1}'.format(res.status_code, res.text))
            sys.exit()


class Splunk():
    def __init__(self):
        self.splunk_ip = '127.0.0.1'
        self.splunk_port = '8089'
        self.sessionkey = sys.stdin.readline().strip()

        self.exec_id = None

        self.config = []
        self.proxy = []

        if len(self.sessionkey) == 0:
            logger.error("Did not receive a session key from splunkd. Please enable passAuth in inputs.conf")
            exit(2)

        self.splunk_session = requests.Session()
        self.splunk_session.verify = False

        self.splunk_session.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Splunk {0}'.format(self.sessionkey)
        }

    def get_config(self):
        try:
            res = self.splunk_session.get('https://{0}:{1}/servicesNS/-/mvuce/storage/passwords?output_mode=json'
                                          .format(self.splunk_ip, self.splunk_port))

            if res.ok:
                for creds in res.json()['entry']:
                    if creds['acl']['app'] == 'mvuce' and creds['content']['realm'] != 'proxy':
                        dict_creds = {}
                        check = re.match(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", creds['content']['username'])
                        if check is not None:
                            logger.debug('Found valid Email Username in passwords. User: {0}'.format(creds['content']['username']))
                            dict_creds['user'] = creds['content']['username']
                            dict_creds['pwd'] = creds['content']['clear_password']
                            dict_creds['cid'] = creds['content']['realm']
                            self.config.append(dict_creds)
                        else:
                            logger.debug(creds['content']['username'] + ' is not a valid email address. Skip.')

                    elif creds['acl']['app'] == 'mvuce' and creds['content']['realm'] == 'proxy':
                        dict_proxy = {}
                        dict_proxy['proxy'] = str(creds['content']['username']).split('|')
                        dict_proxy['userpwd'] = creds['content']['clear_password']
                        self.proxy.append(dict_proxy)

                if len(self.config) > 1:
                    logger.error('Identified more than two MVISION credentials. Please delete password.conf and restart'
                                 ' the Splunk services.')
                    sys.exit()

                if len(self.proxy) > 1:
                    logger.error('Identified more than two Proxy entries. Please delete password.conf and restart'
                                 ' the Splunk services.')
                    sys.exit()

            else:
                logger.error('Error in splunk.get_config(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()
        except Exception as error:
            logger.error('Error in splunk.get_config(). Error: {}'.format(str(error)))
            sys.exit()

    def get_exec_time(self):
        try:
            res = self.splunk_session.get('https://{0}:{1}/servicesNS/nobody/mvuce/storage/collections/data/mvucecol'
                                          .format(self.splunk_ip, self.splunk_port))
            if res.ok:
                if res.json() == []:
                    exec_time = None
                    logger.debug('No Last detection time stamp in mvucecol')
                else:
                    self.exec_id = res.json()[0]['_key']
                    exec_time = res.json()[0]['exec_time']
                    logger.debug('Last detection time stamp in mvucecol: {0}'.format(str(exec_time)))

                return exec_time
            else:
                logger.error('Error in splunk.get_exec_time(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()
        except Exception as error:
            logger.error('Error in splunk.get_exec_time(). Error: {}'.format(str(error)))
            sys.exit()

    def post_exec_time(self, exec_time):
        try:
            payload = {
                'exec_time': exec_time
            }

            if self.exec_id is None:
                url = 'https://{0}:{1}/servicesNS/nobody/mvuce/storage/collections/data/mvucecol'\
                    .format(self.splunk_ip, self.splunk_port)
            else:
                url = 'https://{0}:{1}/servicesNS/nobody/mvuce/storage/collections/data/mvucecol/{2}'\
                    .format(self.splunk_ip, self.splunk_port, self.exec_id)

            res = self.splunk_session.post(url, data=json.dumps(payload))

            if res.ok:
                logger.debug('Successful updated exec_time in mvucecol collection. {0}'.format(str(res.status_code)))
            else:
                logger.error('Error in splunk.post_exec_time(). Error: {} - {}'.format(str(res.status_code), res.text))

        except Exception as error:
            logger.error('Error in splunk.post_exec_time(). Error: {}'.format(str(error)))
            sys.exit()

    def main(self):
        try:
            self.get_config()
            exec_time = self.get_exec_time()

            return exec_time

        except Exception as error:
            logger.error('Error in splunk.main(). Error: {}'.format(str(error)))
            sys.exit()


if __name__ == '__main__':
    splunk = Splunk()
    exec_time = splunk.main()

    uce = UCE(splunk.config, splunk.proxy, exec_time)
    exec_time, logs = uce.get_logs()

    if exec_time is not None:
        splunk.post_exec_time(exec_time)

    for log in logs:
        print(json.dumps(log))

    if len(logs) > 0:
        logger.info('Successfully ingested {0} MVISION UCE Logs'.format(str(len(logs))))
    else:
        logger.debug('No new MVISION UCE Logs retrieved')
