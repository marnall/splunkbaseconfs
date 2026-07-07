# Copyright 2018 ForeScout Technologies

from __future__ import absolute_import
from builtins import object
import os
import json
import shutil
import uuid
import requests
import xml.etree.ElementTree as ElementTree

from fsct_exception import Error
from fsct_ta_config_reader import TAForescoutConfigFetcher
from fsct_rest_api_wrapper import FSSplunkRestApiWrapper
import ipv6utils

import fsct_defaults
from io import open
import six

class FSCounteractActionFetcher(object):

    def __init__(self, logger):
        self.logger = logger

    def get_actions_from_api(self):
        actions_info_data = {}

        # read usessl and verifycert keys from TA app
        ta_config_handle = TAForescoutConfigFetcher(self.logger)
        use_ssl = ta_config_handle.get_usessl()
        verify_cert = ta_config_handle.get_verifycert()
        self.logger.info(
            'Read usessl: [' + use_ssl + '], verify_cert: [' + verify_cert + '] from app: [' + fsct_defaults.FS_TA_APP_NAME + ']')

        # read credentials from TA app
        fsct_emip, auth_token = ta_config_handle.getOneCredential()
        self.logger.info('Read fsct_emip: [%s] from app: [%s]', fsct_emip, fsct_defaults.FS_TA_APP_NAME)

        # create Actions Info request
        protocol = 'https://' if use_ssl == '1' else 'http://'
        verify = True if use_ssl == '1' and verify_cert == '1' else False
        actions_info_url = protocol + fsct_emip + '/splunk/actions_info?' 
        log_action_info_url = ''.join([_f for _f in (protocol, fsct_emip,
                                                     '/splunk/actions_info?') if _f]) 

        # Check if the EM IP is ipv6, add bracket to IPv6 address
        if ipv6utils.is_valid_ipv6_address(fsct_emip):
            actions_info_url = protocol + '[' + fsct_emip + \
                               ']/splunk/actions_info?' 
            log_action_info_url = ''.join([_f for _f in (protocol, '[',
                                                         fsct_emip, ']',
                                                         '/splunk/actions_info?') if _f])

        # Log action info URL without auth_token
        self.logger.debug('Action url: %s', log_action_info_url)

        actions_info_id = uuid.uuid4().hex
        actions_info_data['result'] = {
            'eventtype': 'ct_actions',
            'actions_request_id': actions_info_id
        }

        actions_info_payload = json.dumps(actions_info_data)
        actions_info_response = requests.post(actions_info_url, verify=verify,
                                              data=actions_info_payload.encode('utf-8'), headers={'Authorization': 'CounterACT ' + auth_token})
        # need to remove below line once we get valid xml response from CounterACT
        actions_info_response_content = actions_info_response.text.replace("<br>", "<br/>")
        return self.parse_actions_info_response(actions_info_response_content,
                                                actions_info_id)

    def parse_actions_info_response(self, response, request_id):
        # Delete the logger here
        actions_list = []
        response_xml_tree = ElementTree.fromstring(response)
        response_status = response_xml_tree.find('./STATUS/CODE')
        response_request_id = response_xml_tree.find('./REQUEST_ID')

        if (response_status.text == '200') and (
                request_id == response_request_id.text):
            for node in response_xml_tree.findall('./ACTIONS_INFO/ACTION'):
                action_info = {
                    'name': node.find('NAME').text,
                    'group': node.find('GROUP').text,
                    'disposition': node.find('DISPOSITION').text
                }
                actions_list.append(action_info)
        else:
            raise Error(
                'Unsuccessful Actions Info API call. Invalid status: [' + response_status.text + '] or request ID mismatch')
        return actions_list

    def get_fsct_alert_actions(self):

        # get actions list from CounterACT
        actions_list = self.get_actions_from_api()

        app_bin_dir = os.path.dirname(os.path.realpath(__file__))
        app_root_dir = os.path.dirname(app_bin_dir)

        # read fsct_index value from TA app. This will be populated for each action stanza
        fsct_index = TAForescoutConfigFetcher(self.logger).get_fsct_index()

        # create the directory for alert actions html files, if needed.
        alert_actions_html_dir = os.path.join(app_root_dir, 'default', 'data',
                                              'ui', 'alerts')
        if os.path.exists(alert_actions_html_dir):
            shutil.rmtree(alert_actions_html_dir, ignore_errors=False)
        os.makedirs(alert_actions_html_dir)
        action_data = {}
        fs_actions_list = list(fsct_defaults.FS_SUPPORTED_ACTION_NAMES)
        rest_api_handle = FSSplunkRestApiWrapper(self.logger)

        for action_info in actions_list:
            if action_info.get('name') in fs_actions_list:
                fs_actions_list.remove(action_info.get('name'))
                action_stanza = action_info.get('name') + '_action'
                action_params = {
                    'is_custom': 1,
                    'param.index': fsct_index
                }
                rest_api_handle.updateAlertActionsConf(action_stanza, action_params)

                action_data[action_stanza] = {
                    'action_group': action_info.get('group'),
                    'disposition': action_info.get('disposition')
                }

                # create html file for each action. No need to write anything in it (for now).
                alert_action_html_file = os.path.join(alert_actions_html_dir,
                                                      action_stanza + '.html')
                with open(alert_action_html_file, 'wb') as fh:
                    fh.close()

        # disable the alert actions that are supported but not reported by CounterACT
        for disable_action_name in fs_actions_list:
            action_stanza = disable_action_name + '_action'
            action_params = {
                'is_custom': 0
            }
            rest_api_handle.updateAlertActionsConf(action_stanza, action_params)

        # create parent folder for actions mapping file, if needed.
        conf_file_dest_dir = os.path.join(app_root_dir, 'local')
        if not os.path.exists(conf_file_dest_dir):
            os.makedirs(conf_file_dest_dir)

        # write the action-disposition mapping data inside the mapping file
        actions_disposition_mapping_file = os.path.join(app_root_dir, 'local',
                                                        fsct_defaults.FS_ACTIONS_DISPOSITION_MAPPING_FILE)

        with open(actions_disposition_mapping_file, 'w', encoding='utf8') as fh:
            str_ = json.dumps(action_data, ensure_ascii=False)
            fh.write(six.text_type(str_))
