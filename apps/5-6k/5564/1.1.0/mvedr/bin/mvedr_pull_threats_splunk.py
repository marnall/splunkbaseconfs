#!/usr/bin/env python3
# Written by mohlcyber v.1.1.0 (25.10.2021)
# Script to retrieve all threats from the monitoring dashboard and ingest into Splunk

import os
import sys
import logging.handlers
import requests
import json
import time
import re

from datetime import datetime, timedelta

requests.packages.urllib3.disable_warnings()

logger = logging.getLogger('mvedr_logger')
logger.propagate = False
logger.setLevel(logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/mvedr_logger.log',
                                                    maxBytes=25000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class EDR():
    def __init__(self, creds, proxy, ldtime):
        region = creds[0]['region']
        user = creds[0]['user']
        pwd = creds[0]['pwd']

        if str(region).upper() == 'EU':
            self.base_url = 'soc.eu-central-1.mcafee.com'

        # Only for upgrade from <1.0.6
        elif str(region).upper() == 'US':
            self.base_url = 'soc.mcafee.com'

        elif str(region).upper() == 'US-W':
            self.base_url = 'soc.mcafee.com'
        elif str(region).upper() == 'US-E':
            self.base_url = 'soc.us-east-1.mcafee.com'
        elif str(region).upper() == 'SY':
            self.base_url = 'soc.ap-southeast-2.mcafee.com'
        elif str(region).upper() == 'GOV':
            self.base_url = 'soc.mcafee-gov.com'

        self.edr_session = requests.Session()

        if len(proxy) > 0:
            session_proxy = '{0}://{1}@{2}:{3}'.format(proxy[0]['proxy'][0], proxy[0]['userpwd'], proxy[0]['proxy'][1],
                                                       proxy[0]['proxy'][2])
            self.edr_session.proxies['https'] = session_proxy

        self.edr_session.verify = False
        creds = (user, pwd)
        self.pattern = '%Y-%m-%dT%H:%M:%S.%fZ'

        if ldtime:
            last_detection = datetime.strptime(ldtime, '%Y-%m-%dT%H:%M:%SZ')

            now = datetime.astimezone(datetime.now())
            hours = int(str(now)[-5:].split(':')[0])
            minutes = int(str(now)[-5:].split(':')[1])

            self.last_pulled = (last_detection + timedelta(hours=hours, minutes=minutes, seconds=1)).strftime(self.pattern)
            self.last_check = (last_detection + timedelta(seconds=1)).strftime(self.pattern)
        else:
            self.last_pulled = (datetime.now() - timedelta(days=3)).strftime(self.pattern)
            self.last_check = (datetime.now() - timedelta(days=3)).strftime(self.pattern)

        self.limit = 1000
        self.details = 'True'

        self.auth(creds)

    def auth(self, creds):
        try:
            res = self.edr_session.get('https://api.' + self.base_url + '/identity/v1/login', auth=creds)

            if res.ok:
                logger.debug('Debug edr.auth() - {0} - {1}'.format(res.status_code, res.text))
                token = res.json()['AuthorizationToken']
                self.edr_session.headers = {'Authorization': 'Bearer {}'.format(token)}
            else:
                logger.error('Error in edr.auth(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()
        except Exception as error:
            logger.error('Error in edr.auth(). Error: {}'.format(str(error)))
            sys.exit()

    def get_threats(self):
        try:
            epoch_before = int(time.mktime(time.strptime(self.last_pulled, self.pattern)))

            filter = {}
            severities = ["s0", "s1", "s2", "s3", "s4", "s5"]
            filter['severities'] = severities

            res = self.edr_session.get(
                'https://api.{0}/ft/api/v2/ft/threats?sort=-lastDetected&filter={1}&from={2}&limit={3}'
                .format(self.base_url, json.dumps(filter), str(epoch_before * 1000), str(self.limit)))

            if res.ok:
                logger.debug('Debug edr.get_threats() - {0} - {1}'.format(res.status_code, res.text))
                res = res.json()
                if len(res['threats']) > 0:
                    ldtime = res['threats'][0]['lastDetected']

                    threats_dict = []

                    threats = res['threats']
                    for threat in threats:
                        detections = self.get_detections(threat['id'])
                        threat['url'] = 'https://ui.' + self.base_url + '/monitoring/#/workspace/72,TOTAL_THREATS,{0}' \
                            .format(threat['id'])

                        for detection in detections:
                            threat['detection'] = detection

                            if self.details == 'True':
                                maGuid = detection['host']['maGuid']
                                traceId = detection['traceId']

                                traces = self.get_trace(maGuid, traceId)
                                detection['traces'] = traces

                            threats_dict.append(dict(threat))

                    return ldtime, threats_dict

                else:
                    logger.debug('No new threats identified. Exiting. {0}'.format(res))
                    sys.exit()
            else:
                logger.error('Error in edr.get_threats(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()

        except Exception as error:
            logger.error('Error in edr.get_threats(). Error: {}'.format(str(error)))
            sys.exit()

    def get_detections(self, threatId):
        try:
            last_detected = datetime.strptime(self.last_check, self.pattern)

            res = self.edr_session.get('https://api.' + self.base_url + '/ft/api/v2/ft/threats/{0}/detections'
                                   .format(threatId))

            if res.ok:
                detections = []
                for detection in res.json()['detections']:
                    first_detected = datetime.strptime(detection['firstDetected'], '%Y-%m-%dT%H:%M:%SZ')

                    if first_detected >= last_detected:
                        detections.append(detection)

                return detections
            else:
                logger.error('Error in edr.get_detections(). Error: {} - {}. Continue.'.format(str(res.status_code), res.text))
                return []

        except Exception as error:
            logger.error('Error in edr.get_detections(). Error: {}'.format(str(error)))
            sys.exit()

    def get_trace(self, maGuid, traceId):
        try:
            res = self.edr_session.get('https://api.' + self.base_url +
                                   '/historical/api/v1/traces/main-activity-by-trace-id?maGuid={0}&traceId={1}'
                                   .format(maGuid, traceId))

            logger.debug('Debug edr.get_trace() - {0} - {1}'.format(res.status_code, res.text))
            if res.status_code == 200:
                return res.json()
            else:
                return {}

        except Exception as error:
            logger.error('Error in edr.get_trace(). Error: {}'.format(str(error)))
            sys.exit()


class Splunk():
    def __init__(self):
        self.splunk_ip = '127.0.0.1'
        self.splunk_port = '8089'
        self.sessionkey = sys.stdin.readline().strip()

        self.ldid = None

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
            res = self.splunk_session.get('https://{0}:{1}/servicesNS/-/mvedr/storage/passwords?output_mode=json'
                                          .format(self.splunk_ip, self.splunk_port))

            if res.ok:
                for creds in res.json()['entry']:
                    if creds['acl']['app'] == 'mvedr' and creds['content']['realm'] != 'proxy':
                        dict_creds = {}
                        check = re.match(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", creds['content']['username'])
                        if check is not None:
                            logger.debug('Found valid Email Username in passwords. User: {0}'.format(creds['content']['username']))
                            dict_creds['user'] = creds['content']['username']
                            dict_creds['pwd'] = creds['content']['clear_password']
                            dict_creds['region'] = creds['content']['realm']
                            self.config.append(dict_creds)
                        else:
                            logger.debug(creds['content']['username'] + ' is not a valid email address. Skip.')

                    elif creds['acl']['app'] == 'mvedr' and creds['content']['realm'] == 'proxy':
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

    def get_ldtime(self):
        try:
            res = self.splunk_session.get('https://{0}:{1}/servicesNS/nobody/mvedr/storage/collections/data/mvedrcol'
                                          .format(self.splunk_ip, self.splunk_port))
            if res.ok:
                if res.json() == []:
                    ldtime = None
                    logger.debug('No Last detection time stamp in mvedrcol')
                else:
                    self.ldid = res.json()[0]['_key']
                    ldtime = res.json()[0]['ldtime']
                    logger.debug('Last detection time stamp in mvedrcol: {0}'.format(str(ldtime)))

                return ldtime
            else:
                logger.error('Error in splunk.get_ldtime(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()
        except Exception as error:
            logger.error('Error in splunk.get_ldtime(). Error: {}'.format(str(error)))
            sys.exit()

    def post_ldtime(self, ldtime):
        try:
            payload = {
                'ldtime': ldtime
            }

            if self.ldid is None:
                url = 'https://{0}:{1}/servicesNS/nobody/mvedr/storage/collections/data/mvedrcol'\
                    .format(self.splunk_ip, self.splunk_port)
            else:
                url = 'https://{0}:{1}/servicesNS/nobody/mvedr/storage/collections/data/mvedrcol/{2}'\
                    .format(self.splunk_ip, self.splunk_port, self.ldid)

            res = self.splunk_session.post(url, data=json.dumps(payload))

            if res.ok:
                logger.debug('Successful updated ldtime in mvedrcol collection. {0}'.format(str(res.status_code)))
            else:
                logger.error('Error in splunk.post_ldtime(). Error: {} - {}'.format(str(res.status_code), res.text))

        except Exception as error:
            logger.error('Error in splunk.post_ldtime(). Error: {}'.format(str(error)))
            sys.exit()

    def main(self):
        try:
            self.get_config()
            ldtime = self.get_ldtime()

            return ldtime

        except Exception as error:
            logger.error('Error in splunk.main(). Error: {}'.format(str(error)))
            sys.exit()


if __name__ == '__main__':
    splunk = Splunk()
    ldtime = splunk.main()

    edr = EDR(splunk.config, splunk.proxy, ldtime)
    ldtime, threats = edr.get_threats()

    if ldtime is not None:
        splunk.post_ldtime(ldtime)

    for threat in threats:
        print(json.dumps(threat))
        logger.info('Successfully ingested data for {0}'.format(threat['name']))
