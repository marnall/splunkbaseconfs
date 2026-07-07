#!/usr/bin/env python
""" Copyright start
  Copyright (C) 2008 - 2023 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from fortisoar_common.connection import FortisoarConnection
from fortisoar_common.utils import createEventId
import splunk.clilib.cli_common as scc
import requests
import sys
import csv
import json
from time import sleep
from solnlib import log
log.Logs.set_context(namespace="TA-fortinet-fortisoar")
import io, re
import os, shutil
import time
import splunk.version as ver

version = float(re.search("(\d+.\d+)", ver.__version__).group(1))

if version < 6.4:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
else:
    from splunk.clilib.bundle_paths import make_splunkhome_path


class FortiSOAR(object):
    DEFAULT_RECORD_TYPE = 'alert'
    RECORD_TYPE_URL_MAP = {
        'alert': 'api/triggers/1/splunkAlert',
        'alert-update': 'api/triggers/1/splunkAlertUpdate',
        'incident': 'api/triggers/1/splunkIncident',
        'incident-update': 'api/triggers/1/splunkIncidentUpdate',
    }

    def __init__(self, argv, logger=None, isARaction=False, override_config=False):
        if not logger:
            logger = log.Logs().get_logger('fortisoar_class')
        self.log = logger
        self.change_config = False
        try:
            if not (os.path.isdir(make_splunkhome_path(["etc", "apps", "TA-fortinet-fortisoar", "local"]))):
                os.makedirs(make_splunkhome_path(["etc", "apps", "TA-fortinet-fortisoar", "local"]))
                self.log.debug('local directory created...')
                path = os.getcwd().strip("bin")
                shutil.copy(path + "default/fortisoar.conf", path + "local")
                shutil.copy(path + "default/app.conf", path + "local")
        except Exception as e:
            self.log.error('Not able to create local directory in app. Error: {0}'.format(e))
            raise e
        self.log.info("Start fortisoar")
        self.settings = scc.getConfStanza("fortisoar", "config")
        if isARaction:
            self.system_data = argv
        else:
            self.system_data = sys.stdin.read()
        self.system_data = self.system_data.decode('utf-8') if isinstance(self.system_data, bytes) else self.system_data
        if override_config:
            # check cyops_uri exists or not and update self.settings accordingly
            self.__check_cyops_config(self.system_data)
        self.__updateLogging()
        self.__setEventType(argv.decode() if isinstance(argv, bytes) else argv)
        self.__connectToCS()
        self.base_direct_link = ''
        self.log.info('End init fortisoar')

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
            log.Logs().set_level(logging.DEBUG)

    def __setEventType(self, argv):
        if len(argv) < 2:
            self.record_type = self.DEFAULT_RECORD_TYPE
            self.log.warn('Using default fortisoar record_type "{0}" because none was provided.'.format(
                self.DEFAULT_RECORD_TYPE))
        elif argv[1].lower() not in self.RECORD_TYPE_URL_MAP.keys():
            self.record_type = self.DEFAULT_RECORD_TYPE
            self.log.warn('Using default fortisoar record_type "{0}" because {1} is not a valid value.'.format(
                self.DEFAULT_RECORD_TYPE, argv[1].lower()))
        else:
            self.record_type = argv[1].lower()

        self.endpoint = self.RECORD_TYPE_URL_MAP[self.record_type]
        self.log.info("endpoint: {0}".format(self.endpoint))

    def __setupWriter(self):
        fieldnames = ['Direct Link', 'event_id', '_time']
        self.writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    def __setupReader(self):
        self.log.info('Creating csv reader from stdin')
        sys_data = self.system_data.split('\n\n', 1)[-1]
        self.reader = csv.DictReader(io.StringIO(sys_data.decode('utf-8') if isinstance(sys_data, bytes) else sys_data))
        if self.reader.fieldnames is None:
            self.log.warn("Splunk provided no data to stdin... Exiting")
            exit(0)

    def __readJson(self):
        event = json.loads(self.system_data)
        return event

    def __connectToCS(self):
        self.log.info("Connecting to FortiSOAR")
        self.cs = FortisoarConnection(self.system_data, **self.settings)
        self.log.info("Connected to FortiSOAR")

    def getRecordFromTask(self, task_id):
        MAX_ATTEMPTS = 5
        SUCCESS = False
        endpoint = 'api/wf/api/workflows/?task_id={task_id}'.format(task_id=task_id)
        attempt = 1
        result = {}
        while attempt <= MAX_ATTEMPTS:
            try:
                result = self.cs.getUrl(endpoint)
            except requests.HTTPError:
                sleep(1)
            else:
                if result.get('hydra:member'):
                    status = result.get('hydra:member')[-1].get('status').lower()
                else:
                    sleep(2)
                    continue
                if status == 'finished':
                    SUCCESS = True
                    break
                if status == 'awaiting' or status == 'active':
                    sleep(2)
                    continue
            attempt += 1
        if SUCCESS:
            workflow_iri = result.get('hydra:member')[-1].get('@id')
            endpoint = 'api{workflow_iri}?fields=result'.format(workflow_iri=workflow_iri)
            try:
                result = self.cs.getUrl(endpoint)
                record = result.get('result', '')
                if isinstance(record, list):
                    record = record[0][0] if isinstance(record[0], list) else record[0]
                else:
                    record = result['result']
                record_id = record['@id'].split('/')[-1]
                record_type = record['@type'].lower()
                return self.base_direct_link.format(record_id=record_id, record_type=record_type)
            except Exception as e:
                self.log.error('could not get record id')
        else:
            self.log.error('could not get direct url.')
            return result.get('hydra:member')[-1].get('status')

    def processJsonEvents(self):
        event_data = self.__readJson()
        event = event_data['result']
        if 'event_id' not in event:
            createEventId(event)
        response = self.cs.postUrl(self.endpoint, data=event_data, params={'force_debug': True})
        self.log.info('Task ID: {0}'.format(response['task_id']))

    def processCsvEvents(self):
        self.__setupReader()
        self.__setupWriter()
        self.writer.writeheader()
        for event in self.reader:
            if 'event_id' not in event:
                createEventId(event)
            try:
                response = self.cs.postUrl(self.endpoint, data=event)
                self.log.info('Task ID: {0}'.format(response['task_id']))
                direct_link = self.getRecordFromTask(response['task_id'])
                self.log.info('direct_link: {0}'.format(direct_link))
                self.writer.writerow({'Direct Link': direct_link, 'event_id': event['event_id'], '_time': time.time()})
            except Exception as e:
                self.writer.writerow({'Direct Link': "Failed to add event in FortiSOAR. Please check logs.", 'event_id': event['event_id'], '_time': time.time()})
                raise Exception(e)

    def fetchPlaybooks(self):
        self.log.info('Get CyOps API Trigger Playbooks')
        # list all playbooks that are active, have the configured tag, have API trigger and HMAC auth as the start step
        endpoint = "api/query/workflows?$limit=1000&$relationships=true"
        tag = self.settings.get('tag', None)
        tag_payload_list = []
        if tag:
            tag_payload_list = [{
                "field": "tag",
                "value": "%{0}%".format(tag),
                "display": "",
                "operator": "like",
                "type": "primitive"
            }, {
                "field": "recordTags.uuid",
                "value": [tag],
                "display": "",
                "operator": "in",
                "type": "array"
            }]
        payload = {
            "sort": [],
            "limit": 30,
            "logic": "AND",
            "filters": [
                {
                    "logic": "AND",
                    "filters": [
                        {
                            "field": "isActive",
                            "value": True,
                            "display": "",
                            "operator": "eq",
                            "type": "primitive"
                        },
                        {
                            "field": "steps.stepType",
                            "value": "df26c7a2-4166-4ca5-91e5-548e24c01b5f",
                            "display": "",
                            "operator": "eq",
                            "type": "primitive"
                        }
                    ]
                },
                {
                    "logic": "OR",
                    "filters": tag_payload_list
                }
            ],
            "__selectFields": ["name", "steps"]
        }
        response = self.cs.postUrl(endpoint, payload)

        playbooks = []
        for workflow in response['hydra:member']:
            trigger = None
            for step in workflow['steps']:
                if (step['stepType']['@id'] == '/api/3/workflow_step_types/df26c7a2-4166-4ca5-91e5-548e24c01b5f') \
                        and ('authentication_methods' in step['arguments']) and (
                        step['arguments']['authentication_methods'][0] == ''):
                    trigger = step['arguments']['route']
                    break
            if trigger:
                playbooks.append({'name': workflow['name'], 'trigger': trigger})
        return json.dumps(playbooks)


class FortiSOARWorkflow(FortiSOAR):
    def __init__(self, argv, logger):
        super(FortiSOARWorkflow, self).__init__(argv, logger)
        self.base_direct_link = 'https://{address}/modules/view-panel/{{record_type}}s/{{record_id}}?previousState=main.dashboard'.format(
            address=self.settings['address'])
        self.processCsvEvents()


class FortiSOARAlertActionAlert(FortiSOAR):
    def __init__(self, argv, logger=None):
        argv[1] = 'alert'
        super(FortiSOARAlertActionAlert, self).__init__(argv, logger)
        self.processJsonEvents()


class FortiSOARAlertActionIncident(FortiSOAR):
    def __init__(self, argv, logger=None):
        argv[1] = 'incident'
        super(FortiSOARAlertActionIncident, self).__init__(argv, logger)
        self.processJsonEvents()


class FortiSOARRunPlaybook(FortiSOAR):
    def __init__(self, argv, logger=None):
        super(FortiSOARRunPlaybook, self).__init__(argv, logger, override_config=True)
        event = json.loads(self.system_data)
        if self.change_config:
            endpoint = event.get('configuration', {}).get('cyops_uri').split(self.settings['address'])[1].strip('/')
        else:
            trigger = event['configuration']['playbook']
            endpoint = 'api/triggers/1/{0}'.format(trigger)
        self.log.info('Invoking endpoint: {0}'.format(endpoint))
        response = self.cs.postUrl(endpoint, data=event)
        self.log.info('Task ID: {0}'.format(response['task_id']))
