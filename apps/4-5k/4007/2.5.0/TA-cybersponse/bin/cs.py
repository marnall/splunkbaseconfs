#!/usr/bin/env python
from cybersponse_common.connection import CybersponseConnection
from cybersponse_common.utils import createEventId
import splunk.clilib.cli_common as scc
import requests
import sys
import csv
import json
from time import sleep
from splunktalib.common import log
import io, re
import os, shutil
import splunk.version as ver

version = float(re.search("(\d+.\d+)", ver.__version__).group(1))

if version < 6.4:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
else:
    from splunk.clilib.bundle_paths import make_splunkhome_path


class CyberSponse(object):
    DEFAULT_RECORD_TYPE = 'alert'
    RECORD_TYPE_URL_MAP = {
        'alert': 'api/triggers/1/splunkAlert',
        'alert-update': 'api/triggers/1/splunkAlertUpdate',
        'incident': 'api/triggers/1/splunkIncident',
        'incident-update': 'api/triggers/1/splunkIncidentUpdate',
    }

    def __init__(self, argv, logger=None, isARaction=False, override_config=False):
        if not logger:
            logger = log.Logs('TA-cybersponse').get_logger('cybersponse_class')
        self.log = logger
        self.change_config = False
        try:
            if not (os.path.isdir(make_splunkhome_path(["etc", "apps", "TA-cybersponse", "local"]))):
                os.makedirs(make_splunkhome_path(["etc", "apps", "TA-cybersponse", "local"]))
                self.log.debug('local directory created...')
                path = os.getcwd().strip("bin")
                shutil.copy(path + "default/cybersponse.conf", path + "local")
                shutil.copy(path + "default/app.conf", path + "local")
        except Exception as e:
            self.log.error('Not able to create local directory in app. Error: {}'.format(e))
            raise e
        self.log.info("Start cybersponse")
        self.settings = scc.getConfStanza("cybersponse", "config")
        if isARaction:
            self.system_data = argv
        else:
            self.system_data = sys.stdin.read()
        if override_config:
            # check cyops_uri exists or not and update self.settings accordingly
            self.__check_cyops_config(self.system_data)
        self.__updateLogging()
        self.__setEventType(argv)
        self.__connectToCS()
        self.log.info('End init cybersponse')

    def __check_cyops_config(self, data):
        event_data = json.loads(data)
        cyops_conf = event_data.get('configuration', {})
        if cyops_conf.get('cyops_uri') and cyops_conf.get('cyops_private_key') and cyops_conf.get('cyops_public_key'):
            self.change_config = True
            self.settings.update({'address': cyops_conf.get('cyops_uri').split('/')[2]})
            self.settings.update({'private_key': cyops_conf.get('cyops_private_key')})
            self.settings.update({'public_key': cyops_conf.get('cyops_public_key')})

    def __updateLogging(self):
        if int(self.settings['debug']) > 0:
            import logging
            log.Logs('TA-cybersponse').set_level(logging.DEBUG)

    def __setEventType(self, argv):
        if len(argv) < 2:
            self.record_type = self.DEFAULT_RECORD_TYPE
            self.log.warn('Using default cybersponse record_type "{}" because none was provided.'.format(
                self.DEFAULT_RECORD_TYPE))
        elif argv[1].lower() not in self.RECORD_TYPE_URL_MAP.keys():
            self.record_type = self.DEFAULT_RECORD_TYPE
            self.log.warn('Using default cybersponse record_type "{}" because {} is not a valid value.'.format(
                self.DEFAULT_RECORD_TYPE, argv[1].lower()))
        else:
            self.record_type = argv[1].lower()

        self.endpoint = self.RECORD_TYPE_URL_MAP[self.record_type]
        self.log.info("endpoint: {}".format(self.endpoint))

    def __setupWriter(self):
        fieldnames = ['Direct Link', 'event_id']
        self.writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    def __setupReader(self):
        self.log.info('Creating csv reader from stdin')
        sys_data = self.system_data.split('\n\n', 1)[-1]
        csv_data = []
        self.reader = csv.DictReader(io.StringIO(sys_data.decode('utf-8')))
        if self.reader.fieldnames is None:
            self.log.warn("Splunk provided no data to stdin... Exiting")
            exit(0)

    def __readJson(self):
        event = json.loads(self.system_data)
        return event

    def __connectToCS(self):
        self.log.info("Connecting to CyberSponse")
        self.cs = CybersponseConnection(**self.settings)
        self.log.info("Connected to CyberSponse")

    def getRecordFromTask(self, task_id):
        MAX_ATTEMPTS = 5
        SUCCESS = False
        endpoint = 'api/wf/workflow/healthcheck/job/{}/'.format(task_id)
        attempt = 1
        result = {}
        while attempt <= MAX_ATTEMPTS:
            try:
                result = self.cs.getUrl(endpoint)
            except requests.HTTPError:
                sleep(1)
            else:
                status = result['status'].lower()
                if status == 'success':
                    SUCCESS = True
                    break
                if status == 'pending':
                    sleep(2)
                    continue
            attempt += 1
        if SUCCESS:
            try:
                record = result.get('result', '')
                if isinstance(record, list):
                    record = record[0]
                else:
                    record = result['result']
                record_id = record['@id'].split('/')[-1]
                record_type = record['@type'].lower()
                return self.base_direct_link.format(record_id=record_id, record_type=record_type)
            except Exception as e:
                self.log.error('could not get record id')
        else:
            self.log.error('could not get direct url.')
            return result['status']

    def processJsonEvents(self):
        event_data = self.__readJson()
        event = event_data['result']
        if 'event_id' not in event:
            createEventId(event)
        response = self.cs.postUrl(self.endpoint, data=event_data)
        self.log.info('Task ID: {}'.format(response['task_id']))
        # direct_link = self.getRecordFromTask(response['task_id'])
        # self.log.info('Direct Link: {}'.format(direct_link))

    def processCsvEvents(self):
        self.__setupReader()
        self.__setupWriter()
        self.writer.writeheader()
        for event in self.reader:
            if 'event_id' not in event:
                createEventId(event)
            response = self.cs.postUrl(self.endpoint, data=event)
            self.log.info('Task ID: {}'.format(response['task_id']))
            direct_link = self.getRecordFromTask(response['task_id'])
            self.writer.writerow({'Direct Link': direct_link, 'event_id': event['event_id']})

    def fetchPlaybooks(self):
        self.log.info('Get CyOps API Trigger Playbooks')
        # list all playbooks that are active, have the configured tag, have API trigger and HMAC auth as the start step
        endpoint = 'api/3/workflows?isActive=true&steps__stepType=df26c7a2-4166-4ca5-91e5-548e24c01b5f&$relationships=true&$export=true&$limit=1000'
        tag = self.settings.get('tag', None)
        if tag:
            endpoint = '{0}&tag$like=%25{1}%25'.format(endpoint, tag)
        self.log.info('playbooks filter criteria: {}'.format(endpoint))
        response = self.cs.getUrl(endpoint)
        playbooks = []
        for workflow in response['hydra:member']:
            trigger = None
            for step in workflow['steps']:
                if (step['stepType'] == '/api/3/workflow_step_types/df26c7a2-4166-4ca5-91e5-548e24c01b5f') \
                        and ('authentication_methods' in step['arguments']) and (
                            step['arguments']['authentication_methods'][0] == ''):
                    trigger = step['arguments']['route']
                    break
            if trigger:
                playbooks.append({'name': workflow['name'], 'trigger': trigger})
        return json.dumps(playbooks)


class CyberSponseWorkflow(CyberSponse):
    def __init__(self, argv, logger):
        super(CyberSponseWorkflow, self).__init__(argv, logger)
        self.base_direct_link = 'https://{address}/modules/view-panel/{{record_type}}s/{{record_id}}?previousState=main.dashboard'.format(
            address=self.settings['address'])
        self.processCsvEvents()


class CyberSponseAlertActionAlert(CyberSponse):
    def __init__(self, argv, logger=None):
        argv[1] = 'alert'
        super(CyberSponseAlertActionAlert, self).__init__(argv, logger)
        self.processJsonEvents()


class CyberSponseAlertActionIncident(CyberSponse):
    def __init__(self, argv, logger=None):
        argv[1] = 'incident'
        super(CyberSponseAlertActionIncident, self).__init__(argv, logger)
        self.processJsonEvents()


class CyberSponseRunPlaybook(CyberSponse):
    def __init__(self, argv, logger=None):
        super(CyberSponseRunPlaybook, self).__init__(argv, logger, override_config=True)
        event = json.loads(self.system_data)
        if self.change_config:
            endpoint = event.get('configuration', {}).get('cyops_uri').split(self.settings['address'])[1].strip('/')
        else:
            trigger = event['configuration']['playbook']
            endpoint = 'api/triggers/1/{0}'.format(trigger)
        self.log.info('Invoking endpoint: {0}'.format(endpoint))
        response = self.cs.postUrl(endpoint, data=event)
        self.log.info('Task ID: {}'.format(response['task_id']))
