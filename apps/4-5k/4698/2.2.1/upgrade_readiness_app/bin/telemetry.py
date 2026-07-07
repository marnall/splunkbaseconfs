import os
import re
import sys
import copy
import json
import time
import splunk.rest as sr
from itertools import groupby

if sys.version_info.major == 2:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs_py2'))
elif sys.version_info.major == 3:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs_py3'))

import logger_manager
from consts import *
import utils
import six
from builtins import str
from builtins import range
from builtins import object

telemetry_logging = logger_manager.setup_logging('telemetry')

class Telemetry(object):
    """
    This class deals with collecting telemetry data and sending to Splunk via REST call
    """

    def __init__(self, session_key, request_body):

        self.session_key = session_key
        self.request_body = request_body
        self.telemetry_data = dict()

    def init_telemetry(self):
        """
        Set telemetry entry for a scan if applicable
        """

        TELEMETRY_DATA = {
            'type': "event",
            'component': "app.pythonreadiness.scan",
            'optInRequired': 2,
            'data': {
                'appVersion': "2.2.1",
                'scanType': TELEMETRY_CUSTOM,
                'scanTypeModified': True
            }
        }

        if 'scanType' in self.request_body and self.request_body['scanType']:
            if self.request_body['scanType'] == TYPE_DEPLOYMENT:
                TELEMETRY_DATA['data'].update({
                    'scanType': TELEMETRY_ALL,
                    'scanTypeModified': False
                })
            elif self.request_body['scanType'] == TYPE_SPLUNKBASE:
                TELEMETRY_DATA['data'].update({
                    'scanType': TELEMETRY_SPLUNKBASE
                })
            elif self.request_body['scanType'] == TYPE_PRIVATE:
                TELEMETRY_DATA['data'].update({
                    'scanType': TELEMETRY_PRIVATE
                })

        self.telemetry_data['statistics'] = TELEMETRY_DATA

    def update_telemetry_data(self, report, result, app, app_meta, default):
        """
        Update telemetry data as per the processed report of the app

        :param report: App report
        :param result: Status of the app
        :param app: Name and label of the app
        :param app_meta: Type of app and external link of app
        :param default: Boolean value signifying app is set to PASSED by default

        :return None
        """

        if default:
            meta_data = dict()
            meta_data['source'] = "Splunkbase"
            meta_data['appStatus'] = result
            meta_data['advancedXMLStatus'] = CHECK_CONST_PASSED
            meta_data['advancedXMLNumber'] = 0
            meta_data['cherryPyStatus'] = CHECK_CONST_PASSED
            meta_data['cherryPyNumber'] = 0
            meta_data['MakoXMLStatus'] = CHECK_CONST_PASSED
            meta_data['MakoNumber'] = 0
            meta_data['PythonScriptStatus'] = CHECK_CONST_PASSED
            meta_data['PythonScriptNumber'] = 0
        else:
            meta_data = dict()
            if app_meta[0] == CONST_PRIVATE:
                meta_data['source'] = "Private"
            else:
                meta_data['source'] = "Splunkbase"
            meta_data['appStatus'] = result
            for check in report['checks']:
                if check['name'] == "Advanced XML":
                    meta_data['advancedXMLStatus'] = check['result']
                    file_list = list(entry for entry in check['messages'] if entry['message_filename'] is not None)
                    meta_data['advancedXMLNumber'] = len(file_list)
                elif check['name'] == "Custom CherryPy endpoints":
                    meta_data['cherryPyStatus'] = check['result']
                    file_list = list(entry for entry in check['messages'] if entry['message_filename'] is not None)
                    meta_data['cherryPyNumber'] = len(file_list)
                elif check['name'] == "Python in custom Mako templates":
                    meta_data['MakoXMLStatus'] = check['result']
                    file_list = list(entry for entry in check['messages'] if entry['message_filename'] is not None)
                    meta_data['MakoNumber'] = len(file_list)
                elif check['name'] == "Python scripts":
                    meta_data['PythonScriptStatus'] = check['result']
                    meta_data['PythonScriptNumber'] = len(check['messages'])

        self.telemetry_data['apps'].append({
            'name': app[1],
            'meta': meta_data
        })

    def send_telemetry(self):
        """
        Send data statistics to telemetry endpoint
        """

        counter = 0
        more_data = True
        while more_data:
            data, more_data = self.chunk_data(counter)
            if not data:
                break
            try:
                response, _ = sr.simpleRequest('{}?output_mode=json'.format(telemetry_endpoint),
                                               sessionKey=self.session_key, jsonargs=json.dumps(data), method='POST',
                                               raiseAllErrors=True)
                if response['status'] not in success_codes:
                    telemetry_logging.error("Error Code: {}".format(str(response['status'])))
                else:
                    telemetry_logging.info("Telemetry data uploaded on : {}".format(str(time.asctime())))
            except Exception as e:
                telemetry_logging.exception(str(e))
                break
            counter += 20
            if not more_data:
                break

    def chunk_data(self, counter):
        """
        Divide total data statisitcs in chunks of 20 apps for telemetry

        :param counter: Counter from where the app data should be chunked

        :return chunk, more_data: JSON data of 20 apps, True/False
        """

        apps = self.telemetry_data['apps']
        if counter >= len(apps):
            return {}, False

        chunk = copy.deepcopy(self.telemetry_data['statistics'])
        last_item = counter + 20
        more_data = True
        if last_item > len(apps):
            last_item = len(apps)
            more_data = False
        for item in apps[counter:last_item]:
            chunk['data'].update({
                item['name']: item['meta']
            })
        return chunk, more_data
