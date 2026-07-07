#!/usr/bin/env python3
# Written by mohlcyber v.1.2.0 (02.03.2022)
# Script to retrieve threat events and dlp incidents from MVISION EPO

import os
import sys
import logging.handlers
import requests
import json
import base64

from datetime import datetime, timedelta
from urllib.parse import unquote


logger = logging.getLogger('mvepo_logger')
logger.propagate = False
logger.setLevel(logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/mvepo_logger.log',
                                                    maxBytes=25000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class EPO():
    def __init__(self, creds, proxy, ldtimes):
        self.base_url = 'api-mvprodorg.mvision.mcafee.com'
        self.session = requests.Session()

        if len(proxy) > 0:
            session_proxy = '{0}://{1}@{2}:{3}'.format(proxy[0]['proxy'][0], proxy[0]['userpwd'], proxy[0]['proxy'][1],
                                                       proxy[0]['proxy'][2])
            self.session.proxies['https'] = session_proxy

        self.session.verify = False

        self.tenant = creds[0]['tenant']
        self.user = creds[0]['user']
        self.pw = creds[0]['pwd']

        self.auth()

        self.minutes = 5
        self.events_dict = []
        self.current_ldtimes = ldtimes
        self.updated_ldtimes = []

    def auth(self):
        try:
            iam_url = "https://iam.mcafee-cloud.com/iam/v1.1/token"

            headers = {
                'Accept': 'application/json'
            }

            payload = {
                "username": self.user,
                "password": self.pw,
                "client_id": "0oae8q9q2y0IZOYUm0h7",
                "scope": "epo.evt.r dp.im.r",
                "grant_type": "password"
            }

            if self.tenant != 'Default':
                payload['tenant_id'] = self.tenant

            res = self.session.post(iam_url, headers=headers, data=payload)

            if res.ok:
                access_token = res.json()['access_token']
                headers['Authorization'] = 'Bearer ' + access_token
                self.session.headers = headers
                logger.debug('Debug epo.auth() - {0}'.format(res.status_code))

            if res.status_code != 200:
                logger.error('Error in epo.auth(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()

        except Exception as error:
            logger.error('Error in epo.auth(). Error: {}'.format(str(error)))
            sys.exit()

    def get_events(self, current_ldtime):
        try:
            now = datetime.utcnow()
            nowiso = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'

            params = {
                'type': current_ldtime['type'],
                'since': current_ldtime['time'],
                'until': nowiso,
                'limit': '1000',
                'sort': 'asc'
            }

            nextitem = None
            nextflag = True

            while (nextflag):
                if nextitem:
                    params['since'] = nextitem

                url = 'https://{0}/eventservice/api/v2/events'.format(self.base_url)
                res = self.session.get(url, params=params)
                resp = res.json()

                if res.ok:
                    if len(res.json()['Events']) == 0:
                        logger.debug('No new MVISION EPO {0} identified.'.format(current_ldtime['type']))
                        nextflag = False
                    else:
                        for raw_event in resp['Events']:
                            event = {}
                            event['analyzertype'] = current_ldtime['type']
                            for key, value in raw_event.items():
                                event[key] = value['value']

                            self.events_dict.append(event)

                        if 'Link' in res.headers and 'rel="next"' in res.headers['Link']:
                            nlinks = res.headers['Link'].split(';')
                            nextitem = unquote(nlinks[0]).split('after=')[1]
                            nextitem = json.loads(base64.b64decode(nextitem))['since']
                            nextflag = True
                        else:
                            nextflag = False
                            event_ldtime = resp['Events'][len(resp['Events']) - 1]['receivedutc']['value']
                            check_event_ldtime = datetime.strptime(event_ldtime, '%Y-%m-%dT%H:%M:%S.%fZ')

                            current_event_time = datetime.strptime(current_ldtime['time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            if check_event_ldtime > current_event_time:
                                current_ldtime['time'] = event_ldtime

                else:
                    logger.error('Could not retrieve Events. {0} - {1}'.format(str(res.status_code), res.text))
                    sys.exit()

            self.updated_ldtimes.append(current_ldtime)
            logger.debug('EPO().main() - Updated ldtimes {0}'.format(json.dumps(self.updated_ldtimes)))

        except Exception as error:
            logger.error('Error in epo.get_events(). Error: {}'.format(str(error)))
            sys.exit()

    def main(self):
        if len(self.current_ldtimes) > 0:
            for past_ldtime in self.current_ldtimes:
                last_detection = datetime.strptime(past_ldtime['time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                next_lookup = (last_detection + timedelta(milliseconds=1)).strftime('%Y-%m-%dT%H:%M:%S.%f')
                past_ldtime['time'] = next_lookup[:-3] + 'Z'
        else:
            pull_time = (datetime.utcnow() - timedelta(minutes=self.minutes)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            self.current_ldtimes.append({'_key': None, 'type': 'threats', 'time': pull_time})
            self.current_ldtimes.append({'_key': None, 'type': 'incidents', 'time': pull_time})

        logger.debug('EPO().main() - Current ldtimes {0}'.format(json.dumps(self.current_ldtimes)))

        for current_ldtime in self.current_ldtimes:
            self.get_events(current_ldtime)

        return self.updated_ldtimes, self.events_dict


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
            res = self.splunk_session.get('https://{0}:{1}/servicesNS/-/mvepo/storage/passwords?output_mode=json'
                                          .format(self.splunk_ip, self.splunk_port))
            if res.ok:
                logger.debug('Debug splunk.get_creds() - {0}'.format(res.status_code))
                for creds in res.json()['entry']:
                    if creds['acl']['app'] == 'mvepo' and creds['content']['realm'] != 'proxy':
                        dict_creds = {}
                        dict_creds['tenant'] = creds['content']['realm']
                        dict_creds['user'] = creds['content']['username']
                        dict_creds['pwd'] = creds['content']['clear_password']
                        self.config.append(dict_creds)

                    elif creds['acl']['app'] == 'mvepo' and creds['content']['realm'] == 'proxy':
                        dict_proxy = {}
                        dict_proxy['proxy'] = str(creds['content']['username']).split('|')
                        dict_proxy['userpwd'] = creds['content']['clear_password']
                        self.proxy.append(dict_proxy)

                if len(self.config) > 1:
                    logger.error('Identified more than two MVISION EPO credentials. Please delete password.conf and '
                                 'restart the Splunk services.')
                    sys.exit()

                if len(self.proxy) > 1:
                    logger.error('Identified more than two Proxy entries. Please delete password.conf and restart'
                                 ' the Splunk services.')
                    sys.exit()

            else:
                logger.error('Error in splunk.get_creds(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()
        except Exception as error:
            logger.error('Error in splunk.get_creds(). Error: {}'.format(str(error)))
            sys.exit()

    def get_ldtime(self):
        try:
            ldcol = []

            res = self.splunk_session.get('https://{0}:{1}/servicesNS/nobody/mvepo/storage/collections/data/mvepocol'
                                          .format(self.splunk_ip, self.splunk_port))
            if res.ok:
                if len(res.json()) == 0:
                    logger.debug('No Last detection time stamp in mvepocol')
                else:
                    for entry in res.json():
                        ldcol.append(entry)
                        logger.debug('Last detection time stamp in mvepocol for {0}: {1}'.format(entry['type'], entry['time']))

                return ldcol
            else:
                logger.error('Error in splunk.get_ldtime(). Error: {} - {}'.format(str(res.status_code), res.text))
                sys.exit()
        except Exception as error:
            logger.error('Error in splunk.get_ldtime(). Error: {}'.format(str(error)))
            sys.exit()

    def post_ldtime(self, ldtime):
        try:
            if ldtime['_key'] is None:
                ldtime.pop('_key')
                url = 'https://{0}:{1}/servicesNS/nobody/mvepo/storage/collections/data/mvepocol'\
                    .format(self.splunk_ip, self.splunk_port)
            else:
                url = 'https://{0}:{1}/servicesNS/nobody/mvepo/storage/collections/data/mvepocol/{2}'\
                    .format(self.splunk_ip, self.splunk_port, ldtime['_key'])

            res = self.splunk_session.post(url, data=json.dumps(ldtime))

            if res.ok:
                logger.debug('Successful updated ldtime for {0} in mvepocol collection. {1}'.format(ldtime['type'], res.status_code))
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
            logger.error('Error in splunk.get_creds(). Error: {}'.format(str(error)))
            sys.exit()


if __name__ == '__main__':
    splunk = Splunk()
    ldtimes = splunk.main()

    epo = EPO(splunk.config, splunk.proxy, ldtimes)
    ldtimes, events = epo.main()

    for ldtime in ldtimes:
        splunk.post_ldtime(ldtime)

    for event in events:
        print(json.dumps(event))
        logger.info('Successfully ingested {0} for {1}.'.format(event['analyzertype'], event['analyzerhostname']))

