# Copyright 2018 Forescout Technologies

from __future__ import absolute_import
from builtins import str
import json
import sys
import os
import gzip
import csv
import xml.etree.ElementTree as ET
import zipfile

import requests
from fsct_ta_config_reader import TAForescoutConfigFetcher
import fsct_defaults
import ipv6utils
from io import open

try:
	from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
	from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "TA-forescout_response", "bin", "lib"]))

from cim_actions import ModularAction

CT_EVENT_TO_ALERT_FIELDS = (
	'ctupdate',
	'ip',
	'mac',
	'since',
	'_serial',
	'orig_sid',
	'orig_rid',
	'test_device_id',
	'test_dest',
	'test_target_type',
	'test_http_type',
	'test_url',
	'test_collector_token',
	'test_port',
	'test_transport',
	'ipv6',
	'tenant_id'
)

MAX_EVENTS_PER_ALERT = 2000
MAX_TIMEOUT_IN_SECOND = 600

## ModularAction wrapper
class CounterACTBaseAction(ModularAction):

    def __init__(self, settings, logger, action_name=None):
        super(CounterACTBaseAction, self).__init__(settings, logger, action_name)
        self.index_name  = self.configuration.get('index', '')
        self.action_name = action_name

    def read_action_json(self):
        action_data={}
        app_bin_dir          = os.path.dirname(os.path.realpath(__file__))
        app_root_dir         = os.path.dirname(app_bin_dir)
        actions_mapping_file = os.path.join(app_root_dir, 'local', fsct_defaults.FS_ACTIONS_DISPOSITION_MAPPING_FILE)
        if os.path.exists(actions_mapping_file):
            with open(actions_mapping_file, 'r') as fp:
                action_data = json.load(fp)
        return action_data

    def dowork(self, alert_data, callbackid):
        self.addinfo()
        action_data  = self.read_action_json()
        disposition  = action_data[self.action_name] and action_data[self.action_name]['disposition'] if self.action_name in action_data else None
        action_group = action_data[self.action_name] and action_data[self.action_name]['action_group'] if self.action_name in action_data else None
        self.logger.info("Sending alert to CounterACT with disposition=%s, action_group=%s callback_id=%s", disposition, action_group, callbackid)

        # read usessl and verifycert keys from TA app
        ta_config_handle = TAForescoutConfigFetcher(self.logger)
        use_ssl          = ta_config_handle.get_usessl();
        verify_cert      = ta_config_handle.get_verifycert()
        self.logger.info('Read usessl: [%s], verify_cert: [%s] from app: [%s]',
                         use_ssl, verify_cert, fsct_defaults.FS_TA_APP_NAME)

        # read credentials from TA app
        #fsct_emip, auth_token = ta_config_handle.getCredentials(self.session_key)
        emIps, tokens = ta_config_handle.getCredentials(self.session_key)
        auth_token = ""
        fsct_emip = ""
        if len(emIps) > 1:
            emIpsFromFile          = ta_config_handle.get_fsct_emip()
            callbackIdsFromFile    = ta_config_handle.get_fsct_callbackid()
            for i in range(len(callbackIdsFromFile)):
                if callbackIdsFromFile[i] == callbackid:
                    fsct_emip = emIpsFromFile[i]
                    break

            for i in range(len(emIps)):
                if emIps[i] == fsct_emip:
                    auth_token = tokens[i]
                    break
        else:
            fsct_emip = emIps[0]
            auth_token = tokens[0]

        self.logger.info('Read fsct_emip: [%s] from app: [%s], auth_token: [%s], callback_id: [%s]', fsct_emip,
                         fsct_defaults.FS_TA_APP_NAME, auth_token, callbackid)

        # create URL using action info and config parameters
        protocol           = 'https://' if use_ssl=='1' else 'http://'
        verify             = True if use_ssl == '1' and verify_cert == '1' else False
        alert_url          = protocol + fsct_emip + "/splunk/alerts?disposition=" + disposition + "&action_group=" + action_group
        log_alert_url = ''.join([_f for _f in (protocol, fsct_emip,
                                              "/splunk/alerts?disposition=",
                                              disposition, "&action_group=",
                                              action_group) if _f])

        # Check EM IP is ipv6, then add brackets
        if ipv6utils.is_valid_ipv6_address(fsct_emip):
            alert_url          = protocol + "[" + fsct_emip + "]/splunk/alerts?disposition=" + disposition + "&action_group=" + action_group
            log_alert_url = ''.join([_f for _f in (protocol, '[', fsct_emip, ']',
                                                  "/splunk/alerts?disposition=",
                                                  disposition, "&action_group=",
                                                  action_group) if _f])

        # Log alert_url without auth token
        self.logger.info('Alert URL: %s', log_alert_url)

        alert_payload      = json.dumps(alert_data)

        # For debug only
        #alert_size = len(alert_payload)
        #self.logger.info("Debug only: size of alert is: ", str(alert_size))
        try:
            alert_response     = requests.post(alert_url, verify = verify, data = alert_payload.encode('utf-8'), timeout = 300, headers={'Authorization': 'CounterACT ' + auth_token})
        except requests.exceptions.Timeout:
            self.logger.info("Request to '%s' read timeout. Retrying.", alert_url)
            # Retry once. Maybe we should give specific timeouts for connect and read instead of same value for both
            alert_response = requests.post(alert_url, verify=verify, data=alert_payload.encode('utf-8'), timeout=MAX_TIMEOUT_IN_SECOND, headers={'Authorization': 'CounterACT ' + auth_token})

        alert_response_xml = ET.fromstring(str(alert_response.text))

        self.logger.info('Alert Response: %s', str(alert_response_xml))

        # parse XML response from CounterACT. This response represents the synchronous response to alerts
        action_response_count = 0
        for elem in alert_response_xml:
            if elem.tag == 'ACTION_RESPONSE':
                action_response = ET.tostring(elem)
                events          = str(action_response)
                self.addevent(events, 'counteract_alerts')
                action_response_count += 1
                self.write_log_message(events.replace('\n', '').replace("  ", ''), status='success')
        if action_response_count==0:
            events = str(alert_response.text)
            self.addevent(events, 'counteract_alerts')
            self.write_log_message(events.replace('\n', '').replace('  ', ''), status='failure')
        self.flush_events(
            index=self.index_name,
            success_msg='Created events for synchronous response successfully',
            failure_msg='Failed to create events for synchronous response')

    def write_log_message(self, msg, status):
        if self.log_message:
            self.message(msg, status, rids=self.rids)

    def flush_events(self, index, source = 'modactions',
        success_msg ='Successfully created the events that triggered the action',
        failure_msg ='Failed to create the events that triggered the action'):
        if self.writeevents(index = index, source = source):
            self.write_log_message(success_msg, status = 'success')
        else:
            self.write_log_message(failure_msg, status = 'failure')
        del self.events[:]
        return True

    def perform_mod_action(self):
        alert_data_by_callback = dict()
        if os.path.exists(self.results_file):
            with gzip.open(self.results_file, 'rt') as fh:
                for num, result in enumerate(csv.DictReader(fh)):
                    if 'ip' not in result and 'mac' not in result and 'ipv6' not in result:
                        self.logger.warning('Search result for action: [%s] has none of IP or MAC or IPv6 fields. Ignoring!' % (self.action_name))
                    # Ignore search results that have no '_serial' field
                    if '_serial' not in result:
                        self.logger.error('Search result for action: [%s] has no _serial field. Ignoring!' % (self.action_name))
                        continue
                    tenant_id = result['tenant_id']
                    result.setdefault('rid', str(num))
                    self.update(result)
                    alert_fields = {}
                    # Store all relevant search result fields
                    for event_field in CT_EVENT_TO_ALERT_FIELDS:
                        if event_field in result and result[event_field]:
                            alert_fields[event_field] = result[event_field]

                    # Process alert fields to a format expected by CounterACT
                    alert_fields['ctupdate']  = result['ctupdate'] if 'ctupdate' in result else 'notif'
                    alert_fields['search_id'] = self.sid
                    alert_fields['row_id']    = alert_fields.pop('_serial', '')
                    if 'orig_sid' not in alert_fields:
                        alert_fields['orig_sid'] = ''
                    if 'orig_rid' not in alert_fields:
                        alert_fields['orig_rid'] = ''
                    if tenant_id not in alert_data_by_callback:
                        alert_data_by_callback[tenant_id] = dict()
                        alert_data = dict()
                        alert_data['result'] = {}
                        alert_data['result']['eventtype'] = 'ct_notifications'
                        alert_data['result']['alerts'] = []
                        alert_data_by_callback[tenant_id]['alert_data'] = alert_data

                    alert_data = alert_data_by_callback[tenant_id]['alert_data']
                    alert_data['result']['alerts'].append(alert_fields)
                    alert_data['result']['orig_sid']    = alert_fields['orig_sid']
                    alert_data['result']['search_id']   = alert_fields['search_id']
                    alert_data['result']['search_name'] = self.search_name

                    raw = ''
                    if '_raw' in result:
                        raw = result['_raw']
                    elif 'orig_raw' in result:
                        raw = result['orig_raw']
                    raw = raw.replace('"', "'")

                    if 'ip' in result:
                        self.addevent('raw=\"%s\",search_id=%s,row_id=%s,ip=%s,orig_action_name=%s' % (raw, self.sid, result['_serial'], result['ip'], self.action_name), "counteract_orig_event")
                    else:
                        self.addevent('raw=\"%s\",search_id=%s,row_id=%s,orig_action_name=%s' % (raw, self.sid, result['_serial'], self.action_name), "counteract_orig_event")

                    alert_data_by_callback[tenant_id]['alert_data'] = alert_data
                    if 'result_count' in alert_data_by_callback:
                        result_count = alert_data_by_callback[tenant_id]['result_count']
                    else:
                        result_count = 0
                    if 'eventcount' in result and result['eventcount']:
                        count = result['eventcount']
                    else:
                        count = 0
                    total_count = int(result_count) + int(count)
                    alert_data_by_callback[tenant_id]['result_count'] = total_count
                    self.log_message = 1 if result_count >= 1 else 0
                    if total_count>=MAX_EVENTS_PER_ALERT:
                        self.logger.info("Max events per alert reached for action:[%s]. Will send alert message to CounterACT before processing other search results." % (self.action_name))
                        self.invoke()
                        self.flush_events(index=self.index_name)
                        self.dowork(alert_data, tenant_id)
                        del alert_data_by_callback[tenant_id]['alert_data']['result']['alerts'][:]

                    self.logger.info(str(json.dumps(alert_data_by_callback)))

        for key in alert_data_by_callback:
            if alert_data_by_callback[key]['alert_data']['result']['alerts']:
                self.flush_events(index=self.index_name)
                self.invoke()
                self.dowork(alert_data_by_callback[key]['alert_data'], key)
